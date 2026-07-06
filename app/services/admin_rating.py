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
            LEFT JOIN player p ON p.user_id = a.user_id
            LEFT JOIN discord_auth da ON da.user_id = a.user_id
            ORDER BY
                CASE WHEN a.ahelp_rating_count > 0 THEN 0 ELSE 1 END,
                a.ahelp_rating DESC,
                COALESCE(p.last_seen_user_name, a.user_id::text) ASC
        """)

    result = []
    for i, row in enumerate(rows, start=1):
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
            "place": i,
            "name": row["name"],
            "user_uuid": row["user_uuid"],
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
