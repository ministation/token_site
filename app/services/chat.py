import database_social as social_db


def get_chat_messages(limit: int = 100, after_id: int = 0) -> list[dict]:
    return social_db.get_global_chat_messages(limit, after_id)


def add_chat_message(
    author_id: str,
    author_nickname: str,
    author_avatar: str | None,
    message: str,
    image_url: str | None = None,
) -> dict:
    content = (message or "").strip()
    msg_id = social_db.add_global_chat_message(
        author_id, author_nickname, author_avatar, content, image_url
    )
    messages = social_db.get_global_chat_messages(1, msg_id - 1)
    return messages[-1] if messages else {
        "id": msg_id,
        "author_id": author_id,
        "author_nickname": author_nickname,
        "author_avatar": author_avatar,
        "content": content,
        "image_url": image_url,
    }
