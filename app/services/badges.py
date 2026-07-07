"""Значки участников сайта."""
from datetime import datetime, timezone, timedelta
from app.services.roles import get_staff_role

VETERAN_DAYS = 30


def _parse_created_at(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def get_member_badges(
    discord_username: str = "",
    discord_id: str | None = None,
    created_at=None,
) -> list[dict]:
    badges: list[dict] = []
    role = get_staff_role(discord_username, discord_id)
    if role == "admin":
        badges.append({"id": "admin", "label": "ADMIN", "class": "admin-badge"})
    elif role == "moderator":
        badges.append({"id": "moderator", "label": "MOD", "class": "mod-badge"})
    badges.append({"id": "member", "label": "УЧАСТНИК", "class": "member-badge"})

    created = _parse_created_at(created_at)
    if created and datetime.now(timezone.utc) - created >= timedelta(days=VETERAN_DAYS):
        badges.append({"id": "veteran", "label": "ВЕТЕРАН", "class": "veteran-badge"})
    return badges
