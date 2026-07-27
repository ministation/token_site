import database_social as social_db
from app.config import ADMIN_DISCORD_IDS
from app.services.auth_accounts import is_real_discord_id
from app.services.discord_badges import sync_member_badges
from app.services.game_staff import sync_game_moderator_site_role
from app.services.roles import apply_roles, ROLE_ADMIN


async def sync_roles_from_game(session_data: dict) -> None:
    discord_id = session_data.get("discord_id")
    username = session_data.get("username", "")
    if not is_real_discord_id(discord_id):
        return
    if discord_id and social_db.get_social_user_by_discord_id(discord_id):
        await sync_game_moderator_site_role(discord_id, username)
        await sync_member_badges(discord_id, username)


def apply_staff_flags(session_data: dict) -> dict:
    apply_roles(session_data)
    discord_id = session_data.get("discord_id")
    username = session_data.get("username", "")
    if is_real_discord_id(discord_id) and str(discord_id) in ADMIN_DISCORD_IDS:
        social_db.add_site_staff(discord_id, username, "config", ROLE_ADMIN)
    return session_data
