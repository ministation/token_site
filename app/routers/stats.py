from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
import sqlite3
import os
from app.services.admin_rating import get_admin_rating_leaderboard

router = APIRouter(prefix="/api/stats", tags=["stats"])

SOCIAL_DB_PATH = os.getenv("SOCIAL_DB_PATH", "social.db")
MOSCOW_TZ = timezone(timedelta(hours=3))


def query_snapshots(sql: str, params: tuple = ()):
    conn = sqlite3.connect(SOCIAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/weekly")
async def weekly_online_by_hour():
    """Онлайн по часам за последние 7 дней (средний из снимков)."""
    rows = query_snapshots("""
        SELECT
            strftime('%Y-%m-%d %H:00', timestamp, '+3 hours') AS hour,
            CAST(ROUND(AVG(player_count)) AS INTEGER) AS players
        FROM server_snapshots
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY strftime('%Y-%m-%d %H:00', timestamp, '+3 hours')
        ORDER BY hour
    """)
    return [{"hour": row["hour"], "players": row["players"]} for row in rows]


@router.get("/admin-rating")
async def admin_rating_leaderboard():
    """Рейтинг администрации AHelp из игровой PostgreSQL БД."""
    admins = await get_admin_rating_leaderboard()
    return {
        "updated_at": datetime.now(MOSCOW_TZ).isoformat(),
        "admins": admins,
    }
