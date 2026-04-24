from app.db.database import get_pg_pool

async def get_all_bans(limit: int = 50, offset: int = 0):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                b.ban_id, b.type, b.ban_time, b.expiration_time, b.reason,
                b.banning_admin, b.player_user_id,
                p_admin.last_seen_user_name as admin_name,
                p_player.last_seen_user_name as player_name
            FROM ban b
            LEFT JOIN player p_admin ON b.banning_admin = p_admin.user_id
            LEFT JOIN player p_player ON b.player_user_id = p_player.user_id
            ORDER BY b.ban_time DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
        return [{
            "ban_id": row["ban_id"],
            "type": row["type"],
            "ban_time": row["ban_time"].isoformat() if row["ban_time"] else None,
            "expiration_time": row["expiration_time"].isoformat() if row["expiration_time"] else None,
            "reason": row["reason"],
            "admin_name": row["admin_name"] or "Неизвестный",
            "player_name": row["player_name"] or "Неизвестный",
            "roles": [],
            "rounds": []
        } for row in rows]

async def get_player_bans(player_uuid: str, limit: int = 50):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                b.ban_id, b.type, b.ban_time, b.expiration_time, b.reason,
                p_admin.last_seen_user_name as admin_name,
                p_player.last_seen_user_name as player_name
            FROM ban b
            LEFT JOIN player p_admin ON b.banning_admin = p_admin.user_id
            LEFT JOIN player p_player ON b.player_user_id = p_player.user_id
            WHERE b.player_user_id::text = $1
            ORDER BY b.ban_time DESC
            LIMIT $2
        """, player_uuid, limit)
        return [{
            "ban_id": row["ban_id"],
            "type": row["type"],
            "ban_time": row["ban_time"].isoformat() if row["ban_time"] else None,
            "expiration_time": row["expiration_time"].isoformat() if row["expiration_time"] else None,
            "reason": row["reason"],
            "admin_name": row["admin_name"] or "Неизвестный",
            "player_name": row["player_name"] or "Неизвестный",
        } for row in rows]

async def get_playtime_stats():
    """Статистика по часам игры: новички, обычные, ветераны."""
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE COALESCE(overall_time, interval '0') < interval '50 hours') as newbies,
                COUNT(*) FILTER (WHERE COALESCE(overall_time, interval '0') BETWEEN interval '50 hours' AND interval '400 hours') as regulars,
                COUNT(*) FILTER (WHERE COALESCE(overall_time, interval '0') > interval '400 hours') as veterans,
                COUNT(*) as total
            FROM player_play_time
        """)
        return {
            "newbies": row["newbies"],
            "regulars": row["regulars"],
            "veterans": row["veterans"],
            "total": row["total"]
        }