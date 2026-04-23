import datetime
from typing import List, Dict
from app.config import MAX_CHAT_MESSAGES

# Хранилище сообщений чата в памяти сервера
chat_messages: List[Dict] = []


def get_chat_messages() -> List[Dict]:
    return chat_messages[-50:]  # возвращаем последние 50


def add_chat_message(username: str, avatar: str | None, message: str) -> Dict:
    msg = {
        "username": username,
        "avatar": avatar,
        "message": message.strip(),
        "timestamp": datetime.datetime.now().isoformat()
    }
    chat_messages.append(msg)
    # Ограничиваем максимальное число сообщений
    if len(chat_messages) > MAX_CHAT_MESSAGES:
        chat_messages.pop(0)
    return msg