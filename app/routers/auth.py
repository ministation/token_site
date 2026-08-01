import datetime
import secrets
import aiohttp
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from app.config import (
    ADMIN_DISCORD_IDS,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
    GAME_AUTH_SECRET,
    SITE_PUBLIC_URL,
)
from app.services.auth_session import apply_staff_flags, sync_roles_from_game
from app.services.roles import ROLE_ADMIN, apply_roles
from app.core.sessions import (
    get_session, set_session, delete_session, generate_session_token, user_sessions
)
from app.services.bank import find_player_by_discord
from app.services.game_link import link_discord_account
from app.services.auth_accounts import (
    account_id_for_user,
    is_real_discord_id,
    resolve_social_user,
)
from app.services.referral import apply_referral_code, ensure_referral_code
from app.services.social import get_or_create_social_user
from app.services.avatars import sync_discord_avatar_for_user, resolve_avatar_url
from app.services.site_bans import get_active_ban
from app.services.game_auth_token import verify_site_login_token
import database_social as social_db


async def _sync_roles_from_game(session_data: dict) -> None:
    await sync_roles_from_game(session_data)


def _apply_staff_flags(session_data: dict) -> dict:
    return apply_staff_flags(session_data)


router = APIRouter(tags=["auth"])


@router.get("/login")
async def login(
    request: Request,
    n: str = "",
    e: str = "",
    d: str = "",
    s: str = "",
    c: str = "",
    ref: str = "",
):
    from app.core.ratelimit import enforce_rate, verify_pow_challenge
    enforce_rate(request, "login", limit=8, window=60.0, detail="Слишком много попыток входа.")
    if not verify_pow_challenge(n, e, d, s, c):
        raise HTTPException(
            status_code=400,
            detail="Проверка антибота не пройдена. Обновите страницу и войдите снова.",
        )
    state = secrets.token_urlsafe(16)
    state_data = {"created": datetime.datetime.now().isoformat(), "purpose": "login"}
    ref_code = (ref or request.query_params.get("ref") or "").strip().upper()
    if ref_code:
        state_data["referral_code"] = ref_code
    user_sessions[state] = state_data
    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code&scope=identify&state={state}"
    )
    return RedirectResponse(discord_auth_url)


@router.get("/api/auth/challenge")
async def auth_challenge(request: Request):
    from app.core.ratelimit import enforce_rate, issue_pow_challenge
    enforce_rate(request, "auth_challenge", limit=15, window=60.0)
    return issue_pow_challenge()


@router.get("/callback")
async def callback(request: Request, code: str, state: str):
    from app.core.ratelimit import enforce_rate
    enforce_rate(request, "oauth_callback", limit=15, window=60.0)
    if state not in user_sessions:
        raise HTTPException(status_code=400, detail="Invalid state")

    pending = user_sessions.pop(state)
    purpose = pending.get("purpose", "login")

    # Обмен кода на токен
    async with aiohttp.ClientSession() as session:
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        async with session.post('https://discord.com/api/oauth2/token', data=data, headers=headers) as resp:
            token_data = await resp.json()
            access_token = token_data.get('access_token')

    # Получение данных пользователя Discord
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bearer {access_token}'}
        async with session.get('https://discord.com/api/users/@me', headers=headers) as resp:
            user_data = await resp.json()
            discord_id = user_data['id']
            username = user_data['username']
            avatar = user_data.get('avatar')

    if purpose == "game_link":
        ss14_user_id = pending.get("ss14_user_id")
        if not ss14_user_id:
            raise HTTPException(status_code=400, detail="Не указан игровой аккаунт")
        ok, err = await link_discord_account(ss14_user_id, discord_id)
        if not ok:
            return HTMLResponse(
                f"<h2>Ошибка привязки</h2><p>{err or 'Не удалось привязать аккаунт'}</p>"
                f"<p><a href=\"{SITE_PUBLIC_URL}\">На сайт</a></p>",
                status_code=400,
            )
        player = await find_player_by_discord(discord_id)
        if player:
            get_or_create_social_user(
                player_id=player['player_id'],
                user_uuid=player['user_uuid'],
                discord_id=discord_id,
                discord_username=username,
                discord_avatar=avatar,
                game_nickname=player['last_seen_user_name'],
            )
        return HTMLResponse(
            f"<h2>Готово!</h2><p>Discord успешно привязан к игровому аккаунту.</p>"
            f"<p><a href=\"{SITE_PUBLIC_URL}\">Перейти на сайт</a></p>",
        )

    session_token = generate_session_token()
    session_data = {
        'auth_provider': 'discord',
        'discord_id': discord_id,
        'username': username,
        'created': datetime.datetime.now().isoformat()
    }

    # Привязка к игроку и создание профиля соцсети для всех авторизованных
    player = await find_player_by_discord(discord_id)
    created = False
    if player:
        _, created = get_or_create_social_user(
            player_id=player['player_id'],
            user_uuid=player['user_uuid'],
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            game_nickname=player['last_seen_user_name'],
            return_created=True,
        )
        session_data['player'] = player
    else:
        _, created = get_or_create_social_user(
            player_id=f"discord_{discord_id}",
            user_uuid=f"discord_{discord_id}",
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            game_nickname=username,
            return_created=True,
        )

    try:
        ensure_referral_code(discord_id)
    except Exception:
        pass

    ref_code = pending.get("referral_code")
    if ref_code and created:
        await apply_referral_code(discord_id, ref_code)
        social_db.complete_referral_prompt(discord_id)
    elif created:
        session_data['needs_referral'] = True

    cached_avatar = await sync_discord_avatar_for_user(discord_id, avatar)
    session_data['avatar'] = cached_avatar or resolve_avatar_url(
        social_db.get_social_user_by_discord_id(discord_id)
    )

    await _sync_roles_from_game(session_data)
    _apply_staff_flags(session_data)

    ban = get_active_ban(discord_id)
    if ban:
        return RedirectResponse("/?site_banned=1")

    set_session(session_token, session_data)

    response = RedirectResponse("/?welcome=1" if session_data.get("needs_referral") else "/")
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 3600
    )
    return response


@router.get("/api/auth/game")
async def auth_from_game(request: Request, token: str = ""):
    """Auto-login after SS14 Discord auth service links the account."""
    from app.core.ratelimit import enforce_rate

    enforce_rate(request, "game_auth", limit=20, window=60.0)
    if not GAME_AUTH_SECRET:
        raise HTTPException(status_code=503, detail="Game auth handoff is not configured")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    try:
        payload = verify_site_login_token(token, GAME_AUTH_SECRET, consume=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    discord_id = str(payload["discord_id"])
    if not discord_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid discord_id")
    username = str(payload["username"])[:64]
    avatar = payload.get("avatar")
    ss14_user_id = payload.get("ss14_user_id")

    if ss14_user_id:
        ok, err = await link_discord_account(str(ss14_user_id), discord_id)
        if not ok and err and "уже привязан" in err:
            raise HTTPException(status_code=409, detail=err)

    session_token = generate_session_token()
    session_data = {
        "auth_provider": "discord",
        "discord_id": discord_id,
        "username": username,
        "created": datetime.datetime.now().isoformat(),
    }
    if ss14_user_id:
        session_data["ss14_user_id"] = str(ss14_user_id)

    player = await find_player_by_discord(discord_id)
    created = False
    if player:
        _, created = get_or_create_social_user(
            player_id=player["player_id"],
            user_uuid=player["user_uuid"],
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            game_nickname=player["last_seen_user_name"],
            return_created=True,
        )
        session_data["player"] = player
    else:
        _, created = get_or_create_social_user(
            player_id=f"discord_{discord_id}",
            user_uuid=f"discord_{discord_id}",
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            game_nickname=username,
            return_created=True,
        )

    try:
        ensure_referral_code(discord_id)
    except Exception:
        pass

    if created:
        session_data["needs_referral"] = True

    cached_avatar = await sync_discord_avatar_for_user(discord_id, avatar)
    session_data["avatar"] = cached_avatar or resolve_avatar_url(
        social_db.get_social_user_by_discord_id(discord_id)
    )

    await _sync_roles_from_game(session_data)
    _apply_staff_flags(session_data)

    ban = get_active_ban(discord_id)
    if ban:
        return RedirectResponse("/?site_banned=1")

    set_session(session_token, session_data)
    response = RedirectResponse("/?welcome=1" if session_data.get("needs_referral") else "/")
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=SITE_PUBLIC_URL.startswith("https://"),
        max_age=30 * 24 * 3600,
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token:
        delete_session(session_token)
    response = RedirectResponse("/")
    response.delete_cookie("session_token")
    return response


@router.get("/api/me")
async def api_me(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"authenticated": False}
    session = get_session(session_token)
    if not session:
        return {"authenticated": False}

    discord_id = session.get("discord_id")
    if is_real_discord_id(discord_id):
        player = await find_player_by_discord(discord_id)
        if player:
            session["player"] = player
            get_or_create_social_user(
                player_id=player["player_id"],
                user_uuid=player["user_uuid"],
                discord_id=discord_id,
                discord_username=session["username"],
                discord_avatar=None,
                game_nickname=player["last_seen_user_name"],
            )
            set_session(session_token, session)
    elif session.get("ss14_user_id") and not session.get("player"):
        from app.services.game_link import find_player_by_user_id
        player = await find_player_by_user_id(session["ss14_user_id"])
        if player:
            session["player"] = player
            set_session(session_token, session)

    social = resolve_social_user(session)
    if not social and session.get("discord_id"):
        player = session.get("player")
        if player:
            get_or_create_social_user(
                player_id=player["player_id"],
                user_uuid=player["user_uuid"],
                discord_id=session["discord_id"],
                discord_username=session["username"],
                discord_avatar=None,
                game_nickname=player.get("last_seen_user_name") or session["username"],
            )
        elif is_real_discord_id(session.get("discord_id")):
            get_or_create_social_user(
                player_id=f"discord_{session['discord_id']}",
                user_uuid=f"discord_{session['discord_id']}",
                discord_id=session["discord_id"],
                discord_username=session["username"],
                discord_avatar=None,
                game_nickname=session["username"],
            )
        social = resolve_social_user(session)

    if social and is_real_discord_id(social.get("discord_id")) and not social.get("avatar_custom") and social.get("discord_avatar"):
        cached = await sync_discord_avatar_for_user(session["discord_id"], social.get("discord_avatar"))
        if cached:
            social = resolve_social_user(session)

    result = {
        "authenticated": True,
        "auth_provider": session.get("auth_provider", "discord" if is_real_discord_id(discord_id) else "ss14"),
        "username": session.get("username"),
        "discord_id": discord_id if is_real_discord_id(discord_id) else None,
        "avatar": session.get("avatar"),
        "player": session.get("player"),
        "has_discord": is_real_discord_id(discord_id),
    }
    if social:
        result["social_id"] = social["player_id"]
        result["avatar"] = resolve_avatar_url(social)
        from app.services.presence import status_from_last_seen
        result["presence"] = status_from_last_seen(social.get("last_seen_at"))
        result["display_name"] = social.get("game_nickname") or session.get("username")
    else:
        result["avatar"] = "/static/default_avatar.png"
        result["presence"] = "offline"
        result["display_name"] = session.get("username")

    await _sync_roles_from_game(session)
    apply_roles(result)

    account_id = account_id_for_user(session)
    if is_real_discord_id(session.get("discord_id")) and str(session["discord_id"]) in ADMIN_DISCORD_IDS:
        social_db.add_site_staff(
            session["discord_id"], session.get("username", ""), "config", ROLE_ADMIN
        )

    from app.services.referral import get_referral_info
    try:
        result["referral"] = get_referral_info(account_id) if account_id else None
    except Exception:
        result["referral"] = None

    ban = get_active_ban(session.get("discord_id") if is_real_discord_id(session.get("discord_id")) else None)
    if ban:
        delete_session(session_token)
        return {
            "authenticated": False,
            "site_banned": True,
            "ban_reason": ban.get("reason") or "Нарушение правил",
        }
    return result