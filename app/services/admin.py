import database_social as social_db
from app.services.bank import get_total_stats


async def get_site_statistics() -> dict:
    social = social_db.get_site_stats()
    visits = social_db.get_visit_stats()
    try:
        game_stats = await get_total_stats()
    except Exception:
        game_stats = {}
    return {
        "social": social,
        "visits": visits,
        "game": game_stats,
    }


def list_admins() -> list[dict]:
    return social_db.list_site_admins()


def grant_moderator(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_site_moderator(discord_id, username, granted_by)


def grant_content_maker(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_content_maker(discord_id, username, granted_by or "admin")


def revoke_content_maker(discord_id: str) -> bool:
    return social_db.remove_content_maker(discord_id)


def grant_time_keeper(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_time_keeper(discord_id, username, granted_by or "admin")


def revoke_time_keeper(discord_id: str) -> bool:
    return social_db.remove_time_keeper(discord_id)


def grant_admin(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_site_admin(discord_id, username, granted_by)


def revoke_admin(discord_id: str) -> bool:
    return social_db.remove_site_admin(discord_id)


def find_user_for_admin(username: str) -> dict | None:
    return social_db.get_social_user_by_discord_username(username)
