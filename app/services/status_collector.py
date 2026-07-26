import asyncio
import aiohttp
import sqlite3
import os
from datetime import datetime, timezone

from app.config import GAME_STATUS_URL

SOCIAL_DB_PATH = os.getenv("SOCIAL_DB_PATH", "social.db")


async def fetch_player_count() -> int | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GAME_STATUS_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("players", 0)
    except Exception as e:
        print(f"[Collector] Ошибка получения онлайна: {e}")
    return None


async def store_snapshot(count: int):
    conn = sqlite3.connect(SOCIAL_DB_PATH)
    conn.execute(
        "INSERT INTO server_snapshots (timestamp, player_count) VALUES (?, ?)",
        (datetime.now(timezone.utc).isoformat(), count)
    )
    conn.commit()
    conn.close()


async def collector_loop(interval: int = 300):
    while True:
        count = await fetch_player_count()
        if count is not None:
            await store_snapshot(count)
        await asyncio.sleep(interval)
