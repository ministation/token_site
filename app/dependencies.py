from fastapi import Request, HTTPException
from app.core.sessions import get_session
from app.db.database import get_pg_pool
from app.services.roles import apply_roles
from asyncpg import Pool
import database_social as social_db


async def get_current_user(request: Request) -> dict:
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    session = get_session(session_token)
    if session is None:
        raise HTTPException(status_code=401, detail="Сессия недействительна")
    return apply_roles(session)


async def get_current_player(request: Request) -> dict:
    user = await get_current_user(request)
    if 'player' not in user:
        raise HTTPException(status_code=403, detail="Discord не привязан к игровому аккаунту")
    return user['player']


async def get_current_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Доступ только для администраторов")
    return user


async def get_current_staff(request: Request) -> dict:
    """Администратор или модератор (обжалования)."""
    user = await get_current_user(request)
    if not user.get("is_moderator"):
        raise HTTPException(status_code=403, detail="Доступ только для модерации")
    return user


async def get_optional_user(request: Request) -> dict | None:
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    session = get_session(session_token)
    if session:
        return apply_roles(session)
    return None


async def get_current_social_user(request: Request) -> dict:
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
