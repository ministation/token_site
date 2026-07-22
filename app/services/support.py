import database_social as social_db

ALLOWED_STATUSES = {"open", "answered", "closed"}


def create_ticket(contact: str, subject: str, body: str, player_id: str | None = None) -> int:
    contact = (contact or "").strip()
    subject = (subject or "").strip()
    body = (body or "").strip()
    if len(contact) < 3:
        raise ValueError("Укажите контакт для ответа (почта или Discord)")
    if len(subject) < 3:
        raise ValueError("Тема слишком короткая")
    if len(body) < 10:
        raise ValueError("Опишите вопрос подробнее (мин. 10 символов)")
    if len(contact) > 200 or len(subject) > 200 or len(body) > 4000:
        raise ValueError("Слишком длинный текст")
    return social_db.create_support_ticket(contact, subject, body, player_id)


def list_tickets(status: str | None = None, limit: int = 50, offset: int = 0):
    st = (status or "").strip() or None
    if st and st not in ALLOWED_STATUSES:
        st = None
    return social_db.list_support_tickets(st, limit, offset)


def my_tickets(player_id: str):
    return social_db.list_support_tickets_by_player(player_id)


def get_ticket(ticket_id: int) -> dict | None:
    return social_db.get_support_ticket(ticket_id)


def get_ticket_thread(ticket_id: int) -> dict | None:
    ticket = social_db.get_support_ticket(ticket_id)
    if not ticket:
        return None
    messages = social_db.list_support_ticket_messages(ticket_id)
    return {"ticket": ticket, "messages": messages}


def _validate_message(content: str, image_url: str | None):
    content = (content or "").strip()
    if not content and not image_url:
        raise ValueError("Пустое сообщение")
    if len(content) > 4000:
        raise ValueError("Слишком длинный текст")
    return content


def add_user_message(
    ticket_id: int,
    player_id: str,
    content: str,
    image_url: str | None = None,
    author_name: str | None = None,
) -> int:
    ticket = social_db.get_support_ticket(ticket_id)
    if not ticket:
        raise ValueError("Тикет не найден")
    if ticket.get("player_id") != player_id:
        raise ValueError("Нет доступа к тикету")
    if ticket.get("status") == "closed":
        raise ValueError("Тикет закрыт")
    content = _validate_message(content, image_url)
    return social_db.add_support_ticket_message(
        ticket_id,
        author_type="user",
        content=content,
        author_id=player_id,
        author_name=author_name,
        image_url=image_url,
        new_status="open",
    )


def add_staff_message(
    ticket_id: int,
    content: str,
    reviewed_by: str,
    image_url: str | None = None,
    status: str | None = "answered",
) -> int:
    ticket = social_db.get_support_ticket(ticket_id)
    if not ticket:
        raise ValueError("Тикет не найден")
    content = _validate_message(content, image_url)
    new_status = status if status in ALLOWED_STATUSES else "answered"
    return social_db.add_support_ticket_message(
        ticket_id,
        author_type="staff",
        content=content,
        author_id=reviewed_by,
        author_name=reviewed_by,
        image_url=image_url,
        new_status=new_status,
    )


def set_ticket_status(ticket_id: int, status: str, reviewed_by: str | None = None) -> bool:
    if status not in ALLOWED_STATUSES:
        raise ValueError("Некорректный статус")
    ticket = social_db.get_support_ticket(ticket_id)
    if not ticket:
        raise ValueError("Тикет не найден")
    return social_db.set_support_ticket_status(ticket_id, status, reviewed_by)


def reply_ticket(ticket_id: int, status: str, admin_response: str, reviewed_by: str) -> bool:
    """Legacy: single reply → post as staff message."""
    if status not in ALLOWED_STATUSES:
        raise ValueError("Некорректный статус")
    text = (admin_response or "").strip()
    if text:
        add_staff_message(ticket_id, text, reviewed_by, status=status)
        return True
    return set_ticket_status(ticket_id, status, reviewed_by)
