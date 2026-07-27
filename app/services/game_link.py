import re
import uuid
from typing import Optional

from app.db.database import get_pg_pool

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_valid_user_id(value: str) -> bool:
    return bool(value and _UUID_RE.match(value.strip()))


async def find_player_by_user_id(user_id: str) -> Optional[dict]:
    if not is_valid_user_id(user_id):
        return None
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT player_id, user_id::text AS user_uuid, last_seen_user_name
            FROM player
            WHERE user_id = $1::uuid
            LIMIT 1
            """,
            user_id,
        )
        if not row:
            return None
        return {
            "player_id": str(row["player_id"]),
            "user_uuid": row["user_uuid"],
            "last_seen_user_name": row["last_seen_user_name"],
        }


async def get_discord_id_for_user(user_id: str) -> Optional[str]:
    if not is_valid_user_id(user_id):
        return None
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT discord_id::text FROM discord_auth WHERE user_id = $1::uuid LIMIT 1",
            user_id,
        )
        return row["discord_id"] if row else None


async def get_user_id_for_discord(discord_id: str) -> Optional[str]:
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id::text FROM discord_auth WHERE discord_id = $1::bigint LIMIT 1",
            int(discord_id),
        )
        return row["user_id"] if row else None


async def link_discord_account(user_id: str, discord_id: str) -> tuple[bool, Optional[str]]:
    """Привязывает Discord к SS14-аккаунту в discord_auth."""
    if not is_valid_user_id(user_id):
        return False, "Некорректный ID игрока"

    try:
        discord_int = int(discord_id)
    except (TypeError, ValueError):
        return False, "Некорректный Discord ID"

    player = await find_player_by_user_id(user_id)
    if not player:
        return False, "Игровой аккаунт не найден. Сначала зайдите на сервер."

    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        existing_user = await conn.fetchrow(
            "SELECT discord_id::text FROM discord_auth WHERE user_id = $1::uuid",
            user_id,
        )
        if existing_user:
            if existing_user["discord_id"] == str(discord_int):
                return True, None
            return False, "Этот игровой аккаунт уже привязан к другому Discord"

        existing_discord = await conn.fetchrow(
            "SELECT user_id::text FROM discord_auth WHERE discord_id = $1::bigint",
            discord_int,
        )
        if existing_discord:
            if existing_discord["user_id"] == user_id:
                return True, None
            return False, "Этот Discord уже привязан к другому игровому аккаунту"

        await conn.execute(
            "INSERT INTO discord_auth (user_id, discord_id) VALUES ($1::uuid, $2::bigint)",
            uuid.UUID(user_id),
            discord_int,
        )

    from app.services.referral import grant_pending_referral_coins

    await grant_pending_referral_coins(discord_id, player["user_uuid"])
    return True, None
