import database_social as social_db
from app.services.bank import get_total_stats, get_bank_stats


async def get_site_statistics() -> dict:
    social = social_db.get_site_stats()
    try:
        game_stats = await get_total_stats()
        bank_stats = await get_bank_stats()
    except Exception:
        game_stats = {}
        bank_stats = {}
    return {
        "social": social,
        "game": game_stats,
        "bank": bank_stats,
    }


def list_admins() -> list[dict]:
    return social_db.list_site_admins()


def grant_admin(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_site_admin(discord_id, username, granted_by)


def revoke_admin(discord_id: str) -> bool:
    return social_db.remove_site_admin(discord_id)


def find_user_for_admin(username: str) -> dict | None:
    return social_db.get_social_user_by_discord_username(username)
