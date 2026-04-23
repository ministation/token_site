import datetime
import secrets
import aiohttp
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from app.config import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI
from app.core.sessions import (
    get_session, set_session, delete_session, generate_session_token, user_sessions
)
from app.services.bank import find_player_by_discord
from app.services.social import get_or_create_social_user

router = APIRouter(tags=["auth"])


@router.get("/login")
async def login():
    state = secrets.token_urlsafe(16)
    # Временно сохраняем state (как в оригинале)
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
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png" if avatar else None
    session_data = {
        'discord_id': discord_id,
        'username': username,
        'avatar': avatar_url,
        'created': datetime.datetime.now().isoformat()
    }

    # Привязка к игроку
    player = await find_player_by_discord(discord_id)
    if player:
        session_data['player'] = player
        # Создаем/обновляем профиль соцсети
        get_or_create_social_user(
        player_id=player['player_id'],
        user_uuid=player['user_uuid'],
        discord_id=discord_id,
        discord_username=username,
        discord_avatar=avatar,
        game_nickname=player['last_seen_user_name']
    )

    set_session(session_token, session_data)

    response = RedirectResponse("/")
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=30 * 24 * 3600
    )
    # Удаляем временный state
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
    return {
        "authenticated": True,
        "username": session['username'],
        "discord_id": session['discord_id'],
        "avatar": session.get('avatar'),
        "player": session.get('player')
    }