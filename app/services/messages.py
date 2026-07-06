import database_social as social_db


def send_pm(sender_id: str, receiver_id: str, content: str):
    content = (content or "").strip()
    if not content:
        raise ValueError("Пустое сообщение")
    if len(content) > 2000:
        raise ValueError("Сообщение слишком длинное")
    receiver = social_db.get_social_user_by_player_id(receiver_id)
    if not receiver:
        raise ValueError("Получатель не найден. Он должен хотя бы раз войти на сайт.")
    sender = social_db.get_social_user_by_player_id(sender_id)
    if not sender:
        raise ValueError("Отправитель не найден. Перезайдите через Discord.")
    return social_db.send_private_message(sender_id, receiver_id, content)


def get_pm_conversation(user_id: str, other_id: str, limit=50):
    return social_db.get_conversation(user_id, other_id, limit)


def get_pm_dialogs(user_id: str):
    return social_db.get_user_dialogs(user_id)


def search_pm_users(query: str, exclude_player_id: str, limit=30):
    return social_db.search_message_users(query, exclude_player_id, limit)


def mark_pm_read(user_id: str, other_id: str):
    return social_db.mark_conversation_read(user_id, other_id)
