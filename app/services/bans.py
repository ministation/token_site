from app.db.database import get_pg_pool

async def get_all_bans(limit: int = 50, offset: int = 0):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                b.ban_id,
                b.type,
                b.ban_time,
                b.expiration_time,
                b.reason,
                b.banning_admin,
                COALESCE(bp_agg.players, ARRAY[]::text[]) as players,
                COALESCE(br_agg.roles, ARRAY[]::text[]) as roles,
                COALESCE(brnd_agg.rounds, ARRAY[]::integer[]) as rounds,
                p_admin.last_seen_user_name as admin_name
            FROM ban b
            LEFT JOIN player p_admin ON b.banning_admin = p_admin.user_id
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(bp.user_id::text) as players
                FROM ban_player bp WHERE bp.ban_id = b.ban_id
            ) bp_agg ON true
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(br.role_id) as roles
                FROM ban_role br WHERE br.ban_id = b.ban_id
            ) br_agg ON true
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(brn.round_id) as rounds
                FROM ban_round brn WHERE brn.ban_id = b.ban_id
            ) brnd_agg ON true
            ORDER BY b.ban_time DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
        
        bans = []
        for row in rows:
            bans.append({
                "ban_id": row["ban_id"],
                "type": row["type"],
                "ban_time": row["ban_time"].isoformat() if row["ban_time"] else None,
                "expiration_time": row["expiration_time"].isoformat() if row["expiration_time"] else None,
                "reason": row["reason"] or "Не указана",
                "admin_name": row["admin_name"] or "Неизвестный",
                "players": row["players"] or [],
                "roles": row["roles"] or [],
                "rounds": row["rounds"] or []
            })
        return bans


async def get_player_bans(player_uuid: str, limit: int = 50):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                b.ban_id,
                b.type,
                b.ban_time,
                b.expiration_time,
                b.reason,
                p_admin.last_seen_user_name as admin_name
            FROM ban b
            JOIN ban_player bp ON b.ban_id = bp.ban_id
            LEFT JOIN player p_admin ON b.banning_admin = p_admin.user_id
            WHERE bp.user_id::text = $1
            ORDER BY b.ban_time DESC
            LIMIT $2
        """, player_uuid, limit)
        
        return [{
            "ban_id": row["ban_id"],
            "type": row["type"],
            "ban_time": row["ban_time"].isoformat() if row["ban_time"] else None,
            "expiration_time": row["expiration_time"].isoformat() if row["expiration_time"] else None,
            "reason": row["reason"] or "Не указана",
            "admin_name": row["admin_name"] or "Неизвестный",
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