import datetime
import secrets
import aiohttp
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from app.config import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI
from app.services.roles import apply_roles, ROLE_ADMIN, ROLE_MODERATOR
from app.services.game_staff import sync_game_moderator_site_role
from app.services.discord_badges import sync_member_badges
from app.core.sessions import (
    get_session, set_session, delete_session, generate_session_token, user_sessions
)
from app.services.bank import find_player_by_discord
from app.services.social import get_or_create_social_user
from app.services.avatars import sync_discord_avatar_for_user, resolve_avatar_url
import database_social as social_db


async def _sync_roles_from_game(session_data: dict) -> None:
    discord_id = session_data.get("discord_id")
    username = session_data.get("username", "")
    if discord_id and social_db.get_social_user_by_discord_id(discord_id):
        await sync_game_moderator_site_role(discord_id, username)
        await sync_member_badges(discord_id, username)


def _apply_staff_flags(session_data: dict) -> dict:
    apply_roles(session_data)
    discord_id = session_data.get("discord_id")
    username = session_data.get("username", "")
    if discord_id and session_data.get("is_admin"):
        social_db.add_site_staff(discord_id, username, "config", ROLE_ADMIN)
    elif discord_id and session_data.get("is_moderator"):
        social_db.add_site_staff(discord_id, username, "config", ROLE_MODERATOR)
    return session_data


router = APIRouter(tags=["auth"])


@router.get("/login")
async def login():
    state = secrets.token_urlsafe(16)
    user_sessions[state] = {"created": datetime.datetime.now().isoformat()}
    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code&scope=identify&state={state}"
    )
    return RedirectResponse(discord_auth_url)


@router.get("/callback")
async def callback(code: str, state: str):
    if state not in user_sessions:
        raise HTTPException(status_code=400, detail="Invalid state")

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

    session_token = generate_session_token()
    session_data = {
        'discord_id': discord_id,
        'username': username,
        'created': datetime.datetime.now().isoformat()
    }

    # Привязка к игроку и создание профиля соцсети для всех авторизованных
    player = await find_player_by_discord(discord_id)
    if player:
        session_data['player'] = player
        get_or_create_social_user(
            player_id=player['player_id'],
            user_uuid=player['user_uuid'],
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            game_nickname=player['last_seen_user_name']
        )
    else:
        get_or_create_social_user(
            player_id=f"discord_{discord_id}",
            user_uuid=f"discord_{discord_id}",
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            game_nickname=username
        )

    cached_avatar = await sync_discord_avatar_for_user(discord_id, avatar)
    session_data['avatar'] = cached_avatar or resolve_avatar_url(
        social_db.get_social_user_by_discord_id(discord_id)
    )

    await _sync_roles_from_game(session_data)
    _apply_staff_flags(session_data)
    set_session(session_token, session_data)

    response = RedirectResponse("/")
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=30 * 24 * 3600
    )
    user_sessions.pop(state, None)
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
    from app.services.bank import find_player_by_discord

    # Обновить привязку к игре, если появилась после входа
    player = await find_player_by_discord(session['discord_id'])
    if player:
        session['player'] = player
        get_or_create_social_user(
            player_id=player['player_id'],
            user_uuid=player['user_uuid'],
            discord_id=session['discord_id'],
            discord_username=session['username'],
            discord_avatar=None,
            game_nickname=player['last_seen_user_name']
        )
        from app.core.sessions import set_session
        set_session(session_token, session)

    social = social_db.get_social_user_by_discord_id(session['discord_id'])
    if not social:
        player = session.get('player')
        if player:
            get_or_create_social_user(
                player_id=player['player_id'],
                user_uuid=player['user_uuid'],
                discord_id=session['discord_id'],
                discord_username=session['username'],
                discord_avatar=None,
                game_nickname=player['last_seen_user_name']
            )
        else:
            get_or_create_social_user(
                player_id=f"discord_{session['discord_id']}",
                user_uuid=f"discord_{session['discord_id']}",
                discord_id=session['discord_id'],
                discord_username=session['username'],
                discord_avatar=None,
                game_nickname=session['username']
            )
        social = social_db.get_social_user_by_discord_id(session['discord_id'])
    if social and not social.get("avatar_custom") and social.get("discord_avatar"):
        cached = await sync_discord_avatar_for_user(session["discord_id"], social.get("discord_avatar"))
        if cached:
            social = social_db.get_social_user_by_discord_id(session['discord_id'])
    result = {
        "authenticated": True,
        "username": session['username'],
        "discord_id": session['discord_id'],
        "avatar": session.get('avatar'),
        "player": session.get('player'),
    }
    if social:
        result["social_id"] = social["player_id"]
        result["avatar"] = resolve_avatar_url(social)
        from app.services.presence import status_from_last_seen
        result["presence"] = status_from_last_seen(social.get("last_seen_at"))
    else:
        result["avatar"] = "/static/default_avatar.png"
        result["presence"] = "offline"
    await _sync_roles_from_game(session)
    apply_roles(result)
    if result.get("is_admin"):
        social_db.add_site_staff(session["discord_id"], session.get("username", ""), "config", ROLE_ADMIN)
    elif result.get("is_moderator"):
        social_db.add_site_staff(session["discord_id"], session.get("username", ""), "config", ROLE_MODERATOR)
    return result