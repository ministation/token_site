import database_social as social_db
from app.services.avatars import resolve_avatar_url
from app.services.roles import get_staff_role, get_chat_badges


def format_user_row(row: dict) -> dict:
    discord_id = row.get("discord_id")
    discord_username = row.get("discord_username") or ""
    return {
        "player_id": row["player_id"],
        "game_nickname": row.get("game_nickname") or discord_username or "Игрок",
        "discord_username": discord_username,
        "avatar": resolve_avatar_url(row),
        "author_role": get_staff_role(discord_username, discord_id),
        "badges": get_chat_badges(discord_username, discord_id),
    }


def list_platform_users(exclude_id: str, query: str = "", limit: int = 100, offset: int = 0):
    rows = social_db.list_platform_users(exclude_id, query, limit, offset)
    return [format_user_row(r) for r in rows]
