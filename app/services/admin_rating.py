import uuid

import database_social as social_db
from app.db.database import get_pg_pool

RANK_NAMES: dict[int, str] = {
    23: "Младший модератор",
    24: "Ивент мастер",
    25: "Судья",
    26: "Младший ивент мастер",
    27: "Модератор",
    28: "Куратор",
    29: "Хост",
    31: "Старший модератор",
    33: "Старший ивент мастер",
    37: "Ивент варден",
    41: "Старший ментор",
    42: "Ментор",
    43: "Младший ментор",
    46: "М.Модератор | М.Ивент Мастер",
    47: "М.Модератор | Ивент Мастер",
    48: "Модератор | Ивент мастер",
    50: "Модератор | М.Ивент Мастер",
}

RANK_COLORS: dict[int, str] = {
    23: "#a0c1e0",
    24: "#936122",
    25: "#516cdb",
    26: "#e6c059",
    27: "#6383ff",
    28: "#228b22",
    29: "#ECC5AB",
    31: "#4d53b7",
    33: "#d4843d",
    37: "#a86d38",
    41: "#30e1b9",
    42: "#30e1b9",
    43: "#30e1b9",
    46: "#a0c1e0",
    47: "#936122",
    48: "#6296f6",
    50: "#6296f6",
}


def rank_name(rank_id: int | None) -> str:
    if rank_id is None:
        return "—"
    return RANK_NAMES.get(rank_id, f"Ранг #{rank_id}")


def rank_color(rank_id: int | None) -> str:
    if rank_id is None:
        return "#888888"
    return RANK_COLORS.get(rank_id, "#888888")


async def get_admin_rating_leaderboard() -> list[dict]:
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                a.user_id::text AS user_uuid,
                COALESCE(p.last_seen_user_name, a.user_id::text) AS name,
                da.discord_id::text AS discord_id,
                a.ahelp_rating,
                a.ahelp_rating_count,
                a.admin_rank_id,
                a.deadminned,
                a.suspended
            FROM admin a
            LEFT JOIN LATERAL (
                SELECT last_seen_user_name
                FROM player
                WHERE user_id = a.user_id
                ORDER BY last_seen_time DESC NULLS LAST
                LIMIT 1
            ) p ON true
            LEFT JOIN LATERAL (
                SELECT discord_id
                FROM discord_auth
                WHERE user_id = a.user_id
                ORDER BY discord_id
                LIMIT 1
            ) da ON true
            ORDER BY
                CASE WHEN a.ahelp_rating_count > 0 THEN 0 ELSE 1 END,
                a.ahelp_rating DESC NULLS LAST,
                COALESCE(p.last_seen_user_name, a.user_id::text) ASC,
                a.user_id
        """)

    seen_uuids: set[str] = set()
    result = []
    place = 0
    for row in rows:
        user_uuid = row["user_uuid"]
        if user_uuid in seen_uuids:
            continue
        seen_uuids.add(user_uuid)
        place += 1
        rank_id = row["admin_rank_id"]
        count = int(row["ahelp_rating_count"] or 0)
        rating = float(row["ahelp_rating"]) if count > 0 and row["ahelp_rating"] is not None else None
        player_id = None
        discord_id = row["discord_id"]
        if discord_id:
            social = social_db.get_social_user_by_discord_id(discord_id)
            if social:
                player_id = social["player_id"]
        result.append({
            "place": place,
            "name": row["name"],
            "user_uuid": user_uuid,
            "player_id": player_id,
            "can_message": player_id is not None,
            "rank_id": rank_id,
            "rank_name": rank_name(rank_id),
            "rank_color": rank_color(rank_id),
            "rating": rating,
            "rating_count": count,
            "deadminned": bool(row["deadminned"]),
            "suspended": bool(row["suspended"]),
        })
    return result


async def _recalculate_admin_rating(conn, admin_user_id: str) -> dict:
    uid = uuid.UUID(admin_user_id)
    stats = await conn.fetchrow("""
        SELECT COUNT(*)::int AS cnt, COALESCE(AVG(stars), 0) AS avg
        FROM admin_help_rating
        WHERE admin_user_id = $1
    """, uid)
    cnt = int(stats["cnt"])
    avg = float(stats["avg"]) if cnt > 0 else 0.0
    await conn.execute("""
        UPDATE admin
        SET ahelp_rating_count = $2, ahelp_rating = $3
        WHERE user_id = $1
    """, uid, cnt, avg)
    return {"rating_count": cnt, "rating": avg if cnt > 0 else None}


async def list_admin_help_ratings(admin_user_id: str) -> dict | None:
    pg = await get_pg_pool()
    uid = uuid.UUID(admin_user_id)
    async with pg.acquire() as conn:
        admin_row = await conn.fetchrow("""
            SELECT a.user_id::text AS user_uuid,
                   COALESCE(p.last_seen_user_name, a.user_id::text) AS name,
                   a.ahelp_rating, a.ahelp_rating_count
            FROM admin a
            LEFT JOIN LATERAL (
                SELECT last_seen_user_name
                FROM player
                WHERE user_id = a.user_id
                ORDER BY last_seen_time DESC NULLS LAST
                LIMIT 1
            ) p ON true
            WHERE a.user_id = $1
        """, uid)
        if not admin_row:
            return None

        rows = await conn.fetch("""
            SELECT
                r.admin_help_rating_id AS id,
                r.player_user_id::text AS player_uuid,
                r.admin_user_id::text AS admin_uuid,
                r.round_id,
                r.stars,
                r.created_at,
                COALESCE(p.last_seen_user_name, r.player_user_id::text) AS player_name
            FROM admin_help_rating r
            LEFT JOIN LATERAL (
                SELECT last_seen_user_name
                FROM player
                WHERE user_id = r.player_user_id
                ORDER BY last_seen_time DESC NULLS LAST
                LIMIT 1
            ) p ON true
            WHERE r.admin_user_id = $1
            ORDER BY r.created_at DESC
        """, uid)

    count = int(admin_row["ahelp_rating_count"] or 0)
    rating = float(admin_row["ahelp_rating"]) if count > 0 and admin_row["ahelp_rating"] is not None else None
    return {
        "admin": {
            "user_uuid": admin_row["user_uuid"],
            "name": admin_row["name"],
            "rating": rating,
            "rating_count": count,
        },
        "ratings": [
            {
                "id": row["id"],
                "player_uuid": row["player_uuid"],
                "player_name": row["player_name"],
                "stars": int(row["stars"]),
                "round_id": row["round_id"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ],
    }


async def delete_admin_help_rating(rating_id: int) -> dict | None:
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("""
                SELECT admin_help_rating_id AS id,
                       admin_user_id::text AS admin_uuid,
                       player_user_id::text AS player_uuid,
                       stars
                FROM admin_help_rating
                WHERE admin_help_rating_id = $1
            """, rating_id)
            if not row:
                return None
            await conn.execute(
                "DELETE FROM admin_help_rating WHERE admin_help_rating_id = $1", rating_id
            )
            updated = await _recalculate_admin_rating(conn, row["admin_uuid"])
            return {
                "id": row["id"],
                "admin_uuid": row["admin_uuid"],
                "player_uuid": row["player_uuid"],
                "stars": int(row["stars"]),
                **updated,
            }
