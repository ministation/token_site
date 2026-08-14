"""Чеки для донатов: ручная загрузка PDF админом → страница доната + ЛС игроку.

Интеграция с API «Мой налог» временно отключена (закомментирована ниже).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import database_social as social_db
from app.config import (
    ADMIN_USERNAMES,
    NALOG_AUTO_RECEIPT,
    NALOG_SERVICE_NAME,
    NALOG_TAX_RATE,
    SITE_PUBLIC_URL,
    UPLOAD_DIR,
)

logger = logging.getLogger(__name__)

# --- «Мой налог» API: пока выключено ---
# from app.services.moy_nalog import MoyNalogClient, MoyNalogError, nalog_configured
#
# def nalog_configured() -> bool:
#     ...


def nalog_configured() -> bool:
    """API Мой налог отключён — чеки только вручную."""
    return False


def receipt_service_title(order: dict) -> str:
    product = order.get("tier_name") or "поддержка"
    ptype = order.get("product_type") or "tier"
    kind = "подписка" if ptype == "tier" else "пакет монет"
    template = (NALOG_SERVICE_NAME or "").strip() or (
        "Добровольная поддержка проекта Мини-станция ({product})"
    )
    return template.format(product=product, kind=kind, type=ptype)[:256]


def estimate_tax_rub(amount_rub: float | int) -> float:
    rate = float(NALOG_TAX_RATE or 0.04)
    return round(float(amount_rub or 0) * rate, 2)


def _absolute_url(path: str) -> str:
    base = (SITE_PUBLIC_URL or "").rstrip("/")
    if not path:
        return base
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


def _save_receipt_file(tx_id: str, file_bytes: bytes, *, ext: str = ".pdf") -> str:
    receipts_dir = os.path.join(UPLOAD_DIR, "receipts")
    os.makedirs(receipts_dir, exist_ok=True)
    safe = "".join(c for c in (tx_id or "order") if c.isalnum() or c in "-_")[:36] or "order"
    if not ext.startswith("."):
        ext = f".{ext}"
    ext = ext.lower()
    if ext not in (".pdf", ".png", ".jpg", ".jpeg", ".webp"):
        ext = ".pdf"
    filename = f"receipt_{safe}{ext}"
    path = os.path.join(receipts_dir, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return f"/static/uploads/receipts/{filename}"


def _resolve_receiver_player_id(order: dict) -> str | None:
    pid = (order.get("player_id") or "").strip()
    if pid and not pid.startswith("discord_"):
        user = social_db.get_social_user_by_player_id(pid)
        if user:
            return user["player_id"]
    did = str(order.get("discord_id") or "").strip()
    if did:
        user = social_db.get_social_user_by_discord_id(did)
        if user:
            return user["player_id"]
    if pid.startswith("discord_"):
        user = social_db.get_social_user_by_discord_id(pid.replace("discord_", "", 1))
        if user:
            return user["player_id"]
    return None


def _resolve_pm_sender_id() -> str | None:
    for name in ADMIN_USERNAMES:
        user = social_db.get_social_user_by_discord_username(name)
        if user and user.get("player_id"):
            return user["player_id"]
    return None


def notify_player_receipt(order: dict, *, force: bool = False) -> bool:
    """Шлёт чек в личные сообщения на сайте. True если отправлено."""
    pdf_url = (order.get("receipt_pdf_url") or "").strip()
    if not pdf_url:
        return False
    if order.get("receipt_pm_sent") and not force:
        return True

    receiver_id = _resolve_receiver_player_id(order)
    sender_id = _resolve_pm_sender_id()
    if not receiver_id:
        logger.info("Receipt PM skip: no site user for order %s", order.get("transaction_id"))
        return False
    if not sender_id:
        logger.warning("Receipt PM skip: no admin sender (ADMIN_USERNAMES)")
        return False
    if sender_id == receiver_id:
        social_db.update_donation_order(order["transaction_id"], receipt_pm_sent=1)
        return True

    abs_pdf = _absolute_url(pdf_url)
    amount = order.get("amount_rub") or 0
    name = order.get("tier_name") or "заказ"
    content = (
        f"Чек: «{name}», {amount} ₽\n"
        f"{abs_pdf}"
    )
    try:
        from app.services.messages import send_pm

        send_pm(sender_id, receiver_id, content, image_url=pdf_url)
        social_db.update_donation_order(order["transaction_id"], receipt_pm_sent=1)
        return True
    except Exception:
        logger.exception("Failed to send receipt PM for %s", order.get("transaction_id"))
        return False


def attach_receipt_file(
    order: dict | None,
    *,
    file_bytes: bytes,
    filename: str = "receipt.pdf",
    send_pm: bool = True,
) -> dict:
    """Сохраняет загруженный админом чек и опционально шлёт в ЛС игроку."""
    if not order:
        raise ValueError("Заказ не найден")
    tx_id = order.get("transaction_id") or ""
    if not tx_id:
        raise ValueError("Нет transaction_id")
    if order.get("status") != "confirmed":
        raise ValueError("Чек можно прикрепить только к подтверждённой оплате")
    if not file_bytes:
        raise ValueError("Пустой файл чека")
    if len(file_bytes) > 12 * 1024 * 1024:
        raise ValueError("Файл чека слишком большой (макс. 12 МБ)")

    ext = os.path.splitext(filename or "")[1].lower() or ".pdf"
    if ext not in (".pdf", ".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError("Допустимы PDF или изображение (PNG/JPG/WebP)")

    pdf_url = _save_receipt_file(tx_id, file_bytes, ext=ext)
    social_db.update_donation_order(
        tx_id,
        receipt_pdf_url=pdf_url,
        receipt_url=pdf_url,
        receipt_status="issued",
        receipt_error="",
        receipt_issued_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        receipt_pm_sent=0,
        # пометка, что чек ручной (без API Мой налог)
        receipt_uuid=order.get("receipt_uuid") or f"manual:{tx_id[:12]}",
    )
    order = social_db.get_donation_order_by_tx(tx_id) or order
    if send_pm:
        notify_player_receipt(order, force=True)
    return social_db.get_donation_order_by_tx(tx_id) or order


# ---------------------------------------------------------------------------
# API «Мой налог» — временно отключено. Раскомментировать, когда снова нужно.
# ---------------------------------------------------------------------------
#
# async def issue_receipt_for_order(order, *, force: bool = False) -> dict:
#     """Создаёт чек в «Мой налог», PDF и ЛС игроку."""
#     ... MoyNalogClient().create_income(...) ...
#
# async def maybe_auto_issue_receipt(order):
#     if not order or not NALOG_AUTO_RECEIPT or not nalog_configured():
#         return order
#     return await issue_receipt_for_order(order)


async def issue_receipt_for_order(order: dict | None, *, force: bool = False) -> dict:
    """Заглушка: авто-выдача через Мой налог выключена."""
    raise ValueError(
        "Авто-отправка в «Мой налог» отключена. Прикрепите чек файлом в админке."
    )


async def maybe_auto_issue_receipt(order: dict | None) -> dict | None:
    """Авто-чек через Мой налог выключен — ничего не делаем."""
    # if not order or not NALOG_AUTO_RECEIPT or not nalog_configured():
    #     return order
    # try:
    #     return await issue_receipt_for_order(order)
    # except Exception:
    #     ...
    return order


def nalog_status_payload() -> dict[str, Any]:
    return {
        "configured": False,  # API выключен; чеки только вручную
        "manual_only": True,
        "auto_receipt": False,  # bool(NALOG_AUTO_RECEIPT) — пока всегда False
        "tax_rate": float(NALOG_TAX_RATE or 0.04),
        "service_name_template": NALOG_SERVICE_NAME,
    }
