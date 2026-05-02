import asyncio
import aiohttp
from datetime import datetime, timezone
from app.db.database import get_sqlite_db

# Адрес статуса сервера (можно вынести в конфиг)
STATUS_URL = "http://85.198.118.85:1214/status"

async def fetch_player_count() -> int | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STATUS_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("players", 0)
    except Exception as e:
        print(f"[Collector] Ошибка получения онлайна: {e}")
    return None

async def store_snapshot(count: int):
    db = await get_sqlite_db()
    await db.execute(
        "INSERT INTO server_snapshots (timestamp, player_count) VALUES (?, ?)",
        (datetime.now(timezone.utc).isoformat(), count)
    )
    await db.commit()

async def collector_loop(interval: int = 300):
    """Фоновый цикл сбора данных. Запускается при старте приложения."""
    while True:
        count = await fetch_player_count()
        if count is not None:
            await store_snapshot(count)
        await asyncio.sleep(interval)