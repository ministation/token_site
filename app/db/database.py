import asyncpg
from app.config import DATABASE_CONFIG

pg_pool: asyncpg.Pool | None = None


async def get_pg_pool() -> asyncpg.Pool:
    global pg_pool
    if pg_pool is None:
        pg_pool = await asyncpg.create_pool(**DATABASE_CONFIG, min_size=1, max_size=10)
    return pg_pool


async def close_pg_pool():
    global pg_pool
    if pg_pool:
        await pg_pool.close()
        pg_pool = None