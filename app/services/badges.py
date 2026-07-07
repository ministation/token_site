"""Значки участников сайта."""
from datetime import datetime, timezone, timedelta
import database_social as social_db
from app.services.roles import get_staff_role

VETERAN_DAYS = 30


def _to_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_created_at(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return _to_utc_aware(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return _to_utc_aware(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return _to_utc_aware(datetime.strptime(text, fmt))
        except ValueError:
            continue
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
    if discord_id and social_db.is_content_maker(discord_id):
        badges.append({
            "id": "content_maker",
            "label": "КОНТЕНТ",
            "class": "content-maker-badge",
        })
    badges.append({"id": "member", "label": "УЧАСТНИК", "class": "member-badge"})

    created = _parse_created_at(created_at)
    if created and datetime.now(timezone.utc) - created >= timedelta(days=VETERAN_DAYS):
        badges.append({"id": "veteran", "label": "ВЕТЕРАН", "class": "veteran-badge"})
    return badges
