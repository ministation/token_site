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


def reply_ticket(ticket_id: int, status: str, admin_response: str, reviewed_by: str) -> bool:
    if status not in ALLOWED_STATUSES:
        raise ValueError("Некорректный статус")
    ticket = social_db.get_support_ticket(ticket_id)
    if not ticket:
        raise ValueError("Тикет не найден")
    return social_db.update_support_ticket(
        ticket_id, status, (admin_response or "").strip(), reviewed_by
    )
