from fastapi import Request, HTTPException, Depends
from app.core.sessions import get_session
from app.db.database import get_pg_pool
from asyncpg import Pool


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


async def get_db_pool() -> Pool:
    return await get_pg_pool()