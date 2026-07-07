"""Синхронизация прав staff с игровой PostgreSQL (таблица admin)."""
import database_social as social_db
from app.db.database import get_pg_pool

# Судья, Модератор, Старший модератор
GAME_MODERATOR_RANK_IDS = (25, 27, 31)


async def discord_has_game_moderator_rank(discord_id: str) -> bool:
    if not discord_id:
        return False
    try:
        pg = await get_pg_pool()
        async with pg.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1
                FROM admin a
                JOIN discord_auth da ON da.user_id = a.user_id
                WHERE da.discord_id::text = $1
                  AND a.admin_rank_id = ANY($2::int[])
                  AND COALESCE(a.deadminned, false) = false
                  AND COALESCE(a.suspended, false) = false
                LIMIT 1
                """,
                discord_id,
                list(GAME_MODERATOR_RANK_IDS),
            )
        return row is not None
    except Exception:
        return False


async def sync_game_moderator_site_role(discord_id: str, discord_username: str = "") -> bool:
    """Выдаёт права модератора на сайте игрокам с рангом mod/judge/sr-mod в игре."""
    if not discord_id or not social_db.get_social_user_by_discord_id(discord_id):
        return False
    if not await discord_has_game_moderator_rank(discord_id):
        return False
    social_db.add_site_moderator(discord_id, discord_username or "", "game_db")
    return True


async def sync_all_game_moderators_on_site() -> int:
    """Синхронизирует права модератора для всех зарегистрированных игровых staff."""
    try:
        pg = await get_pg_pool()
        async with pg.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT da.discord_id::text AS discord_id
                FROM admin a
                JOIN discord_auth da ON da.user_id = a.user_id
                WHERE a.admin_rank_id = ANY($1::int[])
                  AND COALESCE(a.deadminned, false) = false
                  AND COALESCE(a.suspended, false) = false
                """,
                list(GAME_MODERATOR_RANK_IDS),
            )
    except Exception:
        return 0
    synced = 0
    for row in rows:
        discord_id = row["discord_id"]
        social = social_db.get_social_user_by_discord_id(discord_id)
        if not social:
            continue
        social_db.add_site_moderator(
            discord_id,
            social.get("discord_username") or "",
            "game_db",
        )
        synced += 1
    return synced
