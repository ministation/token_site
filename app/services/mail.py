"""Простая отправка писем через SMTP (без блокировки event loop)."""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import (
    DONATION_NOTIFY_EMAIL,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_email(
    *,
    subject: str,
    body: str,
    to: str | None = None,
) -> bool:
    """Отправляет письмо. False если SMTP не настроен или ошибка."""
    recipient = (to or DONATION_NOTIFY_EMAIL or "").strip()
    if not recipient:
        logger.warning("Email: нет получателя")
        return False
    if not smtp_configured():
        logger.warning(
            "Email не отправлен (нет SMTP_USER/SMTP_PASSWORD). Тема: %s → %s",
            subject,
            recipient,
        )
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = recipient
    msg.set_content(body)
    try:
        # Короткий timeout: иначе при недоступном SMTP «висит» весь сайт
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Не удалось отправить email на %s", recipient)
        return False


def send_email_background(
    *,
    subject: str,
    body: str,
    to: str | None = None,
) -> None:
    """Ставит отправку в фон — не блокирует ответ API."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        send_email(subject=subject, body=body, to=to)
        return

    async def _run() -> None:
        await asyncio.to_thread(send_email, subject=subject, body=body, to=to)

    loop.create_task(_run())
