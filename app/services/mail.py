"""Простая отправка писем через SMTP."""
from __future__ import annotations

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
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Не удалось отправить email на %s", recipient)
        return False
