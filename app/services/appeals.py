import database_social as social_db


def submit_appeal(ban_id: int, player_id: str, user_uuid: str | None,
                  ckey: str | None, appeal_text: str) -> int:
    text = (appeal_text or "").strip()
    if len(text) < 10:
        raise ValueError("Текст обжалования — минимум 10 символов")
    if len(text) > 2000:
        raise ValueError("Слишком длинный текст")
    return social_db.create_ban_appeal(ban_id, player_id, user_uuid, ckey, text)


def get_my_appeals(player_id: str):
    return social_db.get_appeals_by_player(player_id)


def get_appeal_map(player_id: str) -> dict:
    return social_db.get_appeal_status_map(player_id)


def list_appeals(status: str | None = None, limit: int = 50, offset: int = 0):
    return social_db.list_ban_appeals(status, limit, offset)


def review_appeal(appeal_id: int, status: str, admin_response: str, reviewed_by: str) -> bool:
    if status not in ("approved", "rejected"):
        raise ValueError("Неверный статус")
    return social_db.update_ban_appeal(appeal_id, status, admin_response.strip(), reviewed_by)
