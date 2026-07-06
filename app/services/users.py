import database_social as social_db
from app.services.avatars import resolve_avatar_url


def format_user_row(row: dict) -> dict:
    return {
        "player_id": row["player_id"],
        "game_nickname": row.get("game_nickname") or row.get("discord_username") or "Игрок",
        "discord_username": row.get("discord_username"),
        "avatar": resolve_avatar_url(row),
    }


def list_platform_users(exclude_id: str, query: str = "", limit: int = 100, offset: int = 0):
    rows = social_db.list_platform_users(exclude_id, query, limit, offset)
    return [format_user_row(r) for r in rows]
