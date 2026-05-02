from fastapi import APIRouter, Query
from datetime import datetime, timezone
import sqlite3

router = APIRouter(prefix="/api/online", tags=["online"])

SOCIAL_DB_PATH = "social.db"


def query_snapshots(sql: str, params: tuple = ()):
    conn = sqlite3.connect(SOCIAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/day")
async def online_day(date: str = Query(None, description="Дата в формате YYYY-MM-DD")):
    """Почасовая статистика за выбранный день"""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    rows = query_snapshots("""
        SELECT
            strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
            AVG(player_count) as avg,
            MAX(player_count) as max
        FROM server_snapshots
        WHERE date(timestamp) = date(?)
        GROUP BY strftime('%Y-%m-%d %H', timestamp)
        ORDER BY hour
    """, (date,))
    
    return [
        {
            "hour": row["hour"][-8:-3],
            "avg": round(row["avg"], 1),
            "max": row["max"]
        }
        for row in rows
    ]


@router.get("/week")
async def online_week():
    """Средний и пиковый онлайн за последние 7 дней"""
    rows = query_snapshots("""
        SELECT
            date(timestamp) as day,
            AVG(player_count) as avg,
            MAX(player_count) as max
        FROM server_snapshots
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY day
        ORDER BY day
    """)
    
    return [
        {
            "date": row["day"],
            "avg": round(row["avg"], 1),
            "max": row["max"]
        }
        for row in rows
    ]


@router.get("/month")
async def online_month():
    """Средний и пиковый онлайн за последние 30 дней"""
    rows = query_snapshots("""
        SELECT
            date(timestamp) as day,
            AVG(player_count) as avg,
            MAX(player_count) as max
        FROM server_snapshots
        WHERE timestamp >= datetime('now', '-30 days')
        GROUP BY day
        ORDER BY day
    """)
    
    return [
        {
            "date": row["day"],
            "avg": round(row["avg"], 1),
            "max": row["max"]
        }
        for row in rows
    ]