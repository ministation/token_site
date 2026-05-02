from fastapi import APIRouter, Query
from datetime import datetime, timezone
from app.db.database import get_sqlite_db

router = APIRouter(prefix="/api/online", tags=["online"])

@router.get("/day")
async def online_day(date: str = Query(None, description="Дата в формате YYYY-MM-DD")):
    """Почасовая статистика за выбранный день"""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db = await get_sqlite_db()
    db.row_factory = None
    cursor = await db.execute("""
        SELECT
            strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
            AVG(player_count),
            MAX(player_count)
        FROM server_snapshots
        WHERE date(timestamp) = date(?)
        GROUP BY strftime('%Y-%m-%d %H', timestamp)
        ORDER BY hour
    """, (date,))
    rows = await cursor.fetchall()
    return [
        {
            "hour": r[0][-8:-3],  # HH:MM
            "avg": round(r[1], 1),
            "max": r[2]
        }
        for r in rows
    ]

@router.get("/week")
async def online_week():
    """Средний и пиковый онлайн за последние 7 дней"""
    db = await get_sqlite_db()
    cursor = await db.execute("""
        SELECT
            date(timestamp) as day,
            AVG(player_count),
            MAX(player_count)
        FROM server_snapshots
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY day
        ORDER BY day
    """)
    rows = await cursor.fetchall()
    return [{"date": r[0], "avg": round(r[1], 1), "max": r[2]} for r in rows]

@router.get("/month")
async def online_month():
    """Средний и пиковый онлайн за последние 30 дней"""
    db = await get_sqlite_db()
    cursor = await db.execute("""
        SELECT
            date(timestamp) as day,
            AVG(player_count),
            MAX(player_count)
        FROM server_snapshots
        WHERE timestamp >= datetime('now', '-30 days')
        GROUP BY day
        ORDER BY day
    """)
    rows = await cursor.fetchall()
    return [{"date": r[0], "avg": round(r[1], 1), "max": r[2]} for r in rows]