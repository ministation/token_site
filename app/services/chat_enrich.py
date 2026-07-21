"""Обогащение данных авторов для чатов и ЛС."""
import database_social as social_db
from app.services.avatars import resolve_avatar_url, DEFAULT_AVATAR
from app.services.roles import get_staff_role, ROLE_ADMIN, ROLE_MODERATOR, get_chat_badges
from app.services.presence import status_from_last_seen


def enrich_player_for_chat(player_id: str) -> dict:
    user = social_db.get_social_user_by_player_id(player_id)
    if not user:
        return {
            "player_id": player_id,
            "avatar": DEFAULT_AVATAR,
            "nickname": "Игрок",
            "author_role": None,
            "badges": [],
            "presence": "offline",
        }
    discord_username = user.get("discord_username") or ""
    discord_id = user.get("discord_id")
    role = get_staff_role(discord_username, discord_id)
    return {
        "player_id": player_id,
        "avatar": resolve_avatar_url(user),
        "nickname": user.get("game_nickname") or discord_username or "Игрок",
        "author_role": role,
        "badges": get_chat_badges(discord_username, discord_id),
        "presence": status_from_last_seen(user.get("last_seen_at")),
    }
