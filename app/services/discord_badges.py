"""Синхронизация тэгов контент-мейкера и хранителя времени из Discord."""
import aiohttp
import database_social as social_db
from app.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_GUILD_ID,
    CONTENT_MAKER_ROLE_IDS,
    TIME_KEEPER_ROLE_IDS,
    CONTENT_MAKER_DISCORD_IDS,
    TIME_KEEPER_DISCORD_IDS,
    CONTENT_MAKER_USERNAMES,
    TIME_KEEPER_USERNAMES,
)

AUTO_SOURCES = {"sync", "discord", "config"}


async def fetch_discord_role_ids(discord_id: str) -> list[int]:
    if not DISCORD_BOT_TOKEN or not DISCORD_GUILD_ID or not discord_id:
        return []
    url = f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{discord_id}"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [int(r) for r in data.get("roles", [])]
    except Exception:
        return []


def _has_content_maker_config(discord_id: str, username: str, role_ids: list[int]) -> bool:
    if discord_id in CONTENT_MAKER_DISCORD_IDS:
        return True
    if (username or "").lower() in CONTENT_MAKER_USERNAMES:
        return True
    if CONTENT_MAKER_ROLE_IDS and any(r in CONTENT_MAKER_ROLE_IDS for r in role_ids):
        return True
    return False


def _has_time_keeper_config(discord_id: str, username: str, role_ids: list[int]) -> bool:
    if discord_id in TIME_KEEPER_DISCORD_IDS:
        return True
    if (username or "").lower() in TIME_KEEPER_USERNAMES:
        return True
    if TIME_KEEPER_ROLE_IDS and any(r in TIME_KEEPER_ROLE_IDS for r in role_ids):
        return True
    return False


async def sync_member_badges(discord_id: str, discord_username: str = "") -> None:
    if not discord_id:
        return
    role_ids = await fetch_discord_role_ids(discord_id)
    username = discord_username or ""

    if _has_content_maker_config(discord_id, username, role_ids):
        social_db.add_content_maker(discord_id, username, "sync")
    elif social_db.get_content_maker_source(discord_id) in AUTO_SOURCES:
        social_db.remove_content_maker(discord_id)

    if _has_time_keeper_config(discord_id, username, role_ids):
        social_db.add_time_keeper(discord_id, username, "sync")
    elif social_db.get_time_keeper_source(discord_id) in AUTO_SOURCES:
        social_db.remove_time_keeper(discord_id)


async def sync_all_member_badges() -> int:
    users = social_db.list_all_social_users()
    count = 0
    for user in users:
        discord_id = user.get("discord_id")
        if not discord_id:
            continue
        await sync_member_badges(discord_id, user.get("discord_username") or "")
        count += 1
    return count
