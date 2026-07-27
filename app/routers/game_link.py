import datetime
import secrets

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse

from app.config import (
    DISCORD_CLIENT_ID,
    DISCORD_REDIRECT_URI,
    SITE_PUBLIC_URL,
)
from app.core.sessions import (
    generate_session_token,
    get_session,
    set_session,
    user_sessions,
)
from app.dependencies import get_current_user
from app.services.auth_accounts import is_real_discord_id
from app.services.avatars import resolve_avatar_url, sync_discord_avatar_for_user
from app.services.bank import find_player_by_discord
from app.services.game_link import (
    find_player_by_user_id,
    get_discord_id_for_user,
    is_valid_user_id,
    link_discord_account,
)
from app.services.referral import apply_referral_code, ensure_referral_code
from app.services.site_bans import get_active_ban
from app.services.social import get_or_create_social_user
from app.services.ss14_auth import (
    build_ss14_authorize_url,
    fetch_ss14_profile,
    ss14_oauth_enabled,
    ss14_oauth_public_info,
)
from app.services.auth_session import apply_staff_flags, sync_roles_from_game
import database_social as social_db

router = APIRouter(tags=["game_link"])


def _discord_oauth_url(state: str) -> str:
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code&scope=identify&state={state}"
    )


def _ss14_oauth_url(state: str, nonce: str) -> str:
    return build_ss14_authorize_url(state, nonce)


def _auth_cookie_response(redirect_path: str, session_token: str) -> RedirectResponse:
    response = RedirectResponse(redirect_path)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
    )
    return response


async def _build_ss14_session(
    ss14_user_id: str,
    profile: dict,
    *,
    referral_code: str = "",
) -> tuple[dict, str, bool, str | None]:
    player = await find_player_by_user_id(ss14_user_id)
    if not player:
        return {}, "", False, "Игровой аккаунт не найден. Сначала зайдите на сервер."

    linked_discord = await get_discord_id_for_user(ss14_user_id)
    if linked_discord:
        account_id = str(linked_discord)
        auth_provider = "discord"
    else:
        account_id = f"ss14_{ss14_user_id}"
        auth_provider = "ss14"

    username = (
        player.get("last_seen_user_name")
        or profile.get("preferred_username")
        or profile.get("name")
        or "Игрок"
    )

    _, created = get_or_create_social_user(
        player_id=player["player_id"],
        user_uuid=player["user_uuid"],
        discord_id=account_id,
        discord_username=username,
        discord_avatar=None,
        game_nickname=player["last_seen_user_name"] or username,
        return_created=True,
    )

    try:
        ensure_referral_code(account_id)
    except Exception:
        pass

    if referral_code and created:
        await apply_referral_code(account_id, referral_code)
        social_db.complete_referral_prompt(account_id)

    session_data = {
        "auth_provider": auth_provider,
        "discord_id": account_id,
        "ss14_user_id": ss14_user_id,
        "username": username,
        "player": player,
        "created": datetime.datetime.now().isoformat(),
    }
    if referral_code and created:
        pass
    elif created:
        session_data["needs_referral"] = True

    if is_real_discord_id(account_id):
        cached = await sync_discord_avatar_for_user(account_id, None)
        social = social_db.get_social_user_by_discord_id(account_id)
        session_data["avatar"] = cached or resolve_avatar_url(social)
    else:
        social = social_db.get_social_user_by_discord_id(account_id)
        session_data["avatar"] = resolve_avatar_url(social) if social else "/static/default_avatar.png"

    await sync_roles_from_game(session_data)
    apply_staff_flags(session_data)

    ban = get_active_ban(account_id if is_real_discord_id(account_id) else None)
    if ban:
        return {}, "", False, "site_banned"

    return session_data, account_id, created, None


@router.get("/login/ss14")
async def ss14_login_start(request: Request, ref: str = ""):
    if not ss14_oauth_enabled():
        raise HTTPException(
            status_code=503,
            detail="Вход через SS14 временно недоступен.",
        )
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    state_data = {
        "created": datetime.datetime.now().isoformat(),
        "purpose": "ss14_login",
        "nonce": nonce,
    }
    ref_code = (ref or request.query_params.get("ref") or "").strip().upper()
    if ref_code:
        state_data["referral_code"] = ref_code
    user_sessions[state] = state_data
    return RedirectResponse(_ss14_oauth_url(state, nonce))


@router.get("/login/{user_id}")
async def game_login_link(user_id: str):
    """Точка входа из клиента SS14: привязка Discord к игровому аккаунту."""
    if not is_valid_user_id(user_id):
        raise HTTPException(status_code=400, detail="Некорректный ID игрока")

    player = await find_player_by_user_id(user_id)
    if not player:
        return HTMLResponse(
            "<h2>Аккаунт не найден</h2><p>Сначала зайдите на сервер, затем повторите привязку.</p>",
            status_code=404,
        )

    existing_discord = await get_discord_id_for_user(user_id)
    if existing_discord:
        return HTMLResponse(
            f"<h2>Уже привязано</h2><p>Этот аккаунт уже привязан к Discord.</p>"
            f"<p><a href=\"{SITE_PUBLIC_URL}\">На сайт</a></p>",
        )

    state = secrets.token_urlsafe(16)
    user_sessions[state] = {
        "created": datetime.datetime.now().isoformat(),
        "purpose": "game_link",
        "ss14_user_id": user_id.strip(),
    }
    return RedirectResponse(_discord_oauth_url(state))


@router.get("/api/ss14/link")
async def ss14_link_start(request: Request, user: dict = Depends(get_current_user)):
    """Привязка SS14 к уже открытой Discord-сессии."""
    if not ss14_oauth_enabled():
        raise HTTPException(
            status_code=503,
            detail="Привязка SS14 временно недоступна.",
        )
    if not is_real_discord_id(user.get("discord_id")):
        raise HTTPException(
            status_code=400,
            detail="Сначала войдите через Discord, чтобы привязать SS14.",
        )

    player = await find_player_by_discord(user["discord_id"])
    if player:
        return RedirectResponse("/?ss14_linked=1")

    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    user_sessions[state] = {
        "created": datetime.datetime.now().isoformat(),
        "purpose": "ss14_link",
        "discord_id": user["discord_id"],
        "session_token": request.cookies.get("session_token"),
        "nonce": nonce,
    }
    return RedirectResponse(_ss14_oauth_url(state, nonce))


@router.get("/api/ss14/callback")
async def ss14_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"/?ss14_link_error={error}")
    if not code or state not in user_sessions:
        raise HTTPException(status_code=400, detail="Некорректный ответ SS14")

    pending = user_sessions.pop(state)
    purpose = pending.get("purpose")

    profile, token_err = await fetch_ss14_profile(code)
    if not profile:
        err_code = token_err or "token"
        if err_code in ("invalid_grant", "invalid_client"):
            err_code = "oauth_config"
        return RedirectResponse(f"/?ss14_link_error={err_code}")

    ss14_user_id = profile.get("sub")
    if not ss14_user_id:
        return RedirectResponse("/?ss14_link_error=profile")

    if purpose == "ss14_login":
        session_data, _, _, err = await _build_ss14_session(
            ss14_user_id,
            profile,
            referral_code=pending.get("referral_code", ""),
        )
        if err == "site_banned":
            return RedirectResponse("/?site_banned=1")
        if err:
            return HTMLResponse(
                f"<h2>Не удалось войти</h2><p>{err}</p>"
                f"<p><a href=\"{SITE_PUBLIC_URL}\">На сайт</a></p>",
                status_code=400,
            )
        session_token = generate_session_token()
        set_session(session_token, session_data)
        redirect = "/?welcome=1" if session_data.get("needs_referral") else "/"
        return _auth_cookie_response(redirect, session_token)

    if purpose != "ss14_link":
        raise HTTPException(status_code=400, detail="Неверный тип авторизации")

    discord_id = pending.get("discord_id")
    session_token = pending.get("session_token")
    if not discord_id or not is_real_discord_id(discord_id):
        raise HTTPException(status_code=400, detail="Сессия Discord не найдена")

    ok, err = await link_discord_account(ss14_user_id, discord_id)
    if not ok:
        return RedirectResponse(f"/?ss14_link_error={err or 'link'}")

    player = await find_player_by_user_id(ss14_user_id)
    if player and session_token:
        sess = get_session(session_token)
        if sess and sess.get("discord_id") == discord_id:
            sess["player"] = player
            sess["ss14_user_id"] = ss14_user_id
            set_session(session_token, sess)
            social = social_db.get_social_user_by_discord_id(discord_id)
            if social:
                get_or_create_social_user(
                    player_id=player["player_id"],
                    user_uuid=player["user_uuid"],
                    discord_id=discord_id,
                    discord_username=sess.get("username", social.get("discord_username", "")),
                    discord_avatar=social.get("discord_avatar"),
                    game_nickname=player["last_seen_user_name"],
                )

    return RedirectResponse("/?ss14_linked=1")


@router.get("/api/link/status")
async def link_status(user: dict = Depends(get_current_user)):
    player = user.get("player")
    if not player and is_real_discord_id(user.get("discord_id")):
        player = await find_player_by_discord(user["discord_id"])
    return {
        "linked": bool(player),
        "player": player,
        "ss14_oauth_enabled": ss14_oauth_enabled(),
        "auth_provider": user.get("auth_provider"),
        "has_discord": is_real_discord_id(user.get("discord_id")),
    }


@router.get("/api/auth/providers")
async def auth_providers():
    return {
        "discord": True,
        "ss14": ss14_oauth_enabled(),
        "ss14_setup": ss14_oauth_public_info(),
    }
