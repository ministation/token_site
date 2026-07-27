import datetime
import secrets
import aiohttp
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from urllib.parse import urlencode

from app.config import (
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
    SS14_OAUTH_CLIENT_ID,
    SS14_OAUTH_CLIENT_SECRET,
    SS14_OAUTH_REDIRECT_URI,
    SS14_OAUTH_AUTHORITY,
    SITE_PUBLIC_URL,
)
from app.core.sessions import get_session, set_session, user_sessions
from app.dependencies import get_current_user
from app.services.bank import find_player_by_discord
from app.services.game_link import (
    find_player_by_user_id,
    get_discord_id_for_user,
    is_valid_user_id,
    link_discord_account,
)
from app.services.social import get_or_create_social_user
import database_social as social_db

router = APIRouter(tags=["game_link"])

SS14_AUTH_ENDPOINT = f"{SS14_OAUTH_AUTHORITY.rstrip('/')}/connect/authorize"
SS14_TOKEN_ENDPOINT = f"{SS14_OAUTH_AUTHORITY.rstrip('/')}/connect/token"
SS14_USERINFO_ENDPOINT = f"{SS14_OAUTH_AUTHORITY.rstrip('/')}/connect/userinfo"


def _discord_oauth_url(state: str) -> str:
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code&scope=identify&state={state}"
    )


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
    """Привязка SS14 (Wizard Den) аккаунта к текущей Discord-сессии на сайте."""
    if not SS14_OAUTH_CLIENT_ID or not SS14_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Привязка SS14 временно недоступна. Обратитесь к администрации.",
        )

    player = await find_player_by_discord(user["discord_id"])
    if player:
        return {"ok": True, "already_linked": True, "player": player}

    state = secrets.token_urlsafe(16)
    user_sessions[state] = {
        "created": datetime.datetime.now().isoformat(),
        "purpose": "ss14_link",
        "discord_id": user["discord_id"],
        "session_token": request.cookies.get("session_token"),
    }
    params = urlencode({
        "client_id": SS14_OAUTH_CLIENT_ID,
        "redirect_uri": SS14_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile",
        "state": state,
    })
    return RedirectResponse(f"{SS14_AUTH_ENDPOINT}?{params}")


@router.get("/api/ss14/callback")
async def ss14_link_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"/?ss14_link_error={error}")
    if not code or state not in user_sessions:
        raise HTTPException(status_code=400, detail="Некорректный ответ SS14")

    pending = user_sessions.pop(state)
    if pending.get("purpose") != "ss14_link":
        raise HTTPException(status_code=400, detail="Неверный тип авторизации")

    discord_id = pending.get("discord_id")
    session_token = pending.get("session_token")
    if not discord_id:
        raise HTTPException(status_code=400, detail="Сессия Discord не найдена")

    async with aiohttp.ClientSession() as session:
        token_data = {
            "client_id": SS14_OAUTH_CLIENT_ID,
            "client_secret": SS14_OAUTH_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SS14_OAUTH_REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(SS14_TOKEN_ENDPOINT, data=token_data, headers=headers) as resp:
            tokens = await resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                return RedirectResponse("/?ss14_link_error=token")

        async with session.get(
            SS14_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        ) as resp:
            profile = await resp.json()
            ss14_user_id = profile.get("sub")
            if not ss14_user_id:
                return RedirectResponse("/?ss14_link_error=profile")

    ok, err = await link_discord_account(ss14_user_id, discord_id)
    if not ok:
        return RedirectResponse(f"/?ss14_link_error={err or 'link'}")

    player = await find_player_by_user_id(ss14_user_id)
    if player and session_token:
        sess = get_session(session_token)
        if sess and sess.get("discord_id") == discord_id:
            sess["player"] = player
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
    player = await find_player_by_discord(user["discord_id"])
    ss14_enabled = bool(SS14_OAUTH_CLIENT_ID and SS14_OAUTH_CLIENT_SECRET)
    return {
        "linked": bool(player),
        "player": player,
        "ss14_oauth_enabled": ss14_enabled,
    }
