"""Баны доступа к сайту (не игровые SS14-баны)."""
import database_social as social_db
from app.core.sessions import user_sessions
from app.services.roles import is_admin


def get_active_ban(discord_id: str | None) -> dict | None:
    if not discord_id:
        return None
    return social_db.get_active_site_ban(str(discord_id))


def invalidate_user_sessions(discord_id: str) -> int:
    """Сбрасывает сессии в памяти и в БД."""
    if not discord_id:
        return 0
    tokens = [
        token for token, data in list(user_sessions.items())
        if str((data or {}).get("discord_id") or "") == str(discord_id)
    ]
    for token in tokens:
        user_sessions.pop(token, None)
    return social_db.delete_sessions_for_discord_id(str(discord_id))


def ban_user(
    *,
    target_discord_id: str,
    target_player_id: str | None,
    reason: str,
    admin_discord_id: str | None,
    admin_username: str | None,
    expires_at: str | None = None,
) -> dict:
    target_discord_id = str(target_discord_id or "").strip()
    if not target_discord_id:
        raise ValueError("Не указан Discord ID")
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise ValueError("Укажите причину (минимум 3 символа)")
    if len(reason) > 500:
        raise ValueError("Слишком длинная причина")
    if admin_discord_id and str(admin_discord_id) == target_discord_id:
        raise ValueError("Нельзя забанить самого себя")
    target = social_db.get_social_user_by_discord_id(target_discord_id)
    if target and is_admin(target.get("discord_username", ""), target.get("discord_id")):
        raise ValueError("Нельзя забанить администратора")
    if is_admin("", target_discord_id):
        raise ValueError("Нельзя забанить администратора")

    ban_id = social_db.create_site_ban(
        discord_id=target_discord_id,
        player_id=target_player_id or (target.get("player_id") if target else None),
        reason=reason,
        banned_by_discord_id=admin_discord_id,
        banned_by_username=admin_username,
        expires_at=expires_at,
    )
    invalidate_user_sessions(target_discord_id)
    ban = social_db.get_active_site_ban(target_discord_id) or {"id": ban_id, "reason": reason}
    return ban


def unban_user(discord_id: str, lifted_by: str | None = None) -> bool:
    return social_db.lift_site_ban(str(discord_id), lifted_by=lifted_by)


def unban_by_id(ban_id: int, lifted_by: str | None = None) -> bool:
    return social_db.lift_site_ban_by_id(ban_id, lifted_by=lifted_by)


def list_bans(active_only: bool = True, limit: int = 50, offset: int = 0) -> list[dict]:
    return social_db.list_site_bans(active_only=active_only, limit=limit, offset=offset)
