from fastapi import Request, HTTPException, Depends
from app.core.sessions import get_session
from app.db.database import get_pg_pool
from asyncpg import Pool
import database_social as social_db


async def get_current_user(request: Request) -> dict:
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    session = get_session(session_token)
    if session is None:
        raise HTTPException(status_code=401, detail="Сессия недействительна")
    return session


async def get_current_player(request: Request) -> dict:
    user = await get_current_user(request)
    if 'player' not in user:
        raise HTTPException(status_code=403, detail="Discord не привязан к игровому аккаунту")
    return user['player']


async def get_optional_user(request: Request) -> dict | None:
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    return get_session(session_token)


async def get_current_social_user(request: Request) -> dict:
    """Авторизованный пользователь с записью в social_users."""
    user = await get_current_user(request)
    social = social_db.get_social_user_by_discord_id(user['discord_id'])
    if not social:
        raise HTTPException(status_code=403, detail="Профиль не найден. Перезайдите через Discord.")
    return {**user, 'social': social, 'social_id': social['player_id']}


async def get_optional_social_user(request: Request) -> dict | None:
    user = await get_optional_user(request)
    if not user:
        return None
    social = social_db.get_social_user_by_discord_id(user['discord_id'])
    if not social:
        return None
    return {**user, 'social': social, 'social_id': social['player_id']}


async def get_db_pool() -> Pool:
    return await get_pg_pool()