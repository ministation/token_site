import database_social as social_db

def send_pm(sender_id: str, receiver_id: str, content: str):
    receiver = social_db.get_social_user_by_player_id(receiver_id)
    if not receiver:
        raise ValueError("Получатель не найден")
    return social_db.send_private_message(sender_id, receiver_id, content)

def get_pm_conversation(user_id: str, other_id: str, limit=50):
    return social_db.get_conversation(user_id, other_id, limit)

def get_pm_dialogs(user_id: str):
    return social_db.get_user_dialogs(user_id)