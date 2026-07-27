import database_social as social_db


def is_placeholder_account_id(account_id: str | None) -> bool:
    if not account_id:
        return True
    return str(account_id).startswith(("discord_", "ss14_"))


def is_real_discord_id(discord_id: str | None) -> bool:
    return bool(discord_id) and not is_placeholder_account_id(discord_id)


def account_id_for_user(user: dict) -> str | None:
    discord_id = user.get("discord_id")
    if discord_id:
        return str(discord_id)
    ss14_user_id = user.get("ss14_user_id")
    if ss14_user_id:
        return f"ss14_{ss14_user_id}"
    player = user.get("player") or {}
    user_uuid = player.get("user_uuid")
    if user_uuid:
        return f"ss14_{user_uuid}"
    return None


def resolve_social_user(user: dict) -> dict | None:
    discord_id = user.get("discord_id")
    if discord_id:
        social = social_db.get_social_user_by_discord_id(str(discord_id))
        if social:
            return social
    player = user.get("player") or {}
    if player.get("player_id"):
        social = social_db.get_social_user_by_player_id(player["player_id"])
        if social:
            return social
    ss14_user_id = user.get("ss14_user_id") or player.get("user_uuid")
    if ss14_user_id:
        return social_db.get_social_user_by_user_uuid(str(ss14_user_id))
    return None
