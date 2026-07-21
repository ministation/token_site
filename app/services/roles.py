"""Роли staff на сайте: admin (полный доступ) и moderator (админ-панель + обжалования)."""
import database_social as social_db
from app.config import ADMIN_USERNAMES, MODERATOR_USERNAMES

ROLE_ADMIN = "admin"
ROLE_MODERATOR = "moderator"
ROLE_CONTENT_MAKER = "content_maker"


def get_staff_role(username: str = "", discord_id: str | None = None) -> str | None:
    """Возвращает основную staff-роль: 'admin', 'moderator' или None."""
    if discord_id:
        db_role = social_db.get_site_staff_role(discord_id)
        if db_role == ROLE_ADMIN:
            return ROLE_ADMIN
        if db_role == ROLE_MODERATOR:
            return ROLE_MODERATOR
    uname = (username or "").lower()
    if uname and uname in ADMIN_USERNAMES:
        return ROLE_ADMIN
    if uname and uname in MODERATOR_USERNAMES:
        return ROLE_MODERATOR
    return None


def get_chat_badges(discord_username: str = "", discord_id: str | None = None) -> list[dict]:
    """Значки для чатов: ADMIN, MOD, КОНТЕНТ."""
    badges: list[dict] = []
    role = get_staff_role(discord_username, discord_id)
    if role == ROLE_ADMIN:
        badges.append({"id": "admin", "label": "ADMIN", "class": "admin-badge"})
    elif role == ROLE_MODERATOR:
        badges.append({"id": "moderator", "label": "MOD", "class": "mod-badge"})
    if discord_id and social_db.is_content_maker(discord_id):
        badges.append({
            "id": "content_maker",
            "label": "КОНТЕНТ",
            "class": "content-maker-badge",
        })
    if discord_id and social_db.is_time_keeper(discord_id):
        badges.append({
            "id": "time_keeper",
            "label": "ХРАНИТЕЛЬ",
            "class": "time-keeper-badge",
        })
    return badges


def is_admin(username: str = "", discord_id: str | None = None) -> bool:
    return get_staff_role(username, discord_id) == ROLE_ADMIN


def is_moderator(username: str = "", discord_id: str | None = None) -> bool:
    role = get_staff_role(username, discord_id)
    return role in (ROLE_ADMIN, ROLE_MODERATOR)


def is_staff(username: str = "", discord_id: str | None = None) -> bool:
    return get_staff_role(username, discord_id) is not None


def apply_roles(session: dict) -> dict:
    discord_id = session.get("discord_id")
    role = get_staff_role(session.get("username", ""), discord_id)
    session["staff_role"] = role
    session["is_admin"] = role == ROLE_ADMIN
    session["is_moderator"] = role in (ROLE_ADMIN, ROLE_MODERATOR)
    session["is_content_maker"] = bool(discord_id and social_db.is_content_maker(discord_id))
    session["is_time_keeper"] = bool(discord_id and social_db.is_time_keeper(discord_id))
    return session


def get_role_by_author_id(author_player_id: str) -> str | None:
    user = social_db.get_social_user_by_player_id(author_player_id)
    if not user:
        return None
    return get_staff_role(user.get("discord_username", ""), user.get("discord_id"))
