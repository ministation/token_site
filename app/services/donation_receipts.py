"""Выдача чеков НПД: PDF на сайте + ЛС игроку."""

from __future__ import annotations

import io
import logging
import os
import tempfile
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
from app.services.moy_nalog import MoyNalogClient, MoyNalogError, nalog_configured

logger = logging.getLogger(__name__)


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


def _build_receipt_pdf(
    *,
    order: dict,
    print_url: str,
    print_bytes: bytes | None = None,
    print_ctype: str = "",
) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Mini-station / NPD receipt", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.ln(4)
    lines = [
        f"Order: {(order.get('transaction_id') or '')[:36]}",
        f"Item: {order.get('tier_name') or '—'}",
        f"Amount: {order.get('amount_rub') or 0} RUB",
        f"Date: {order.get('created_at') or datetime.now(timezone.utc).isoformat()}",
    ]
    for line in lines:
        pdf.cell(0, 8, line.encode("latin-1", "replace").decode("latin-1"), ln=True)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Official receipt link:", ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(0, 80, 180)
    pdf.multi_cell(0, 6, print_url)
    pdf.set_text_color(0, 0, 0)

    # Встраиваем печатную форму, если это картинка
    ctype = (print_ctype or "").lower()
    if print_bytes and any(x in ctype for x in ("png", "jpeg", "jpg", "image")):
        suffix = ".png" if "png" in ctype else ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(print_bytes)
            tmp_path = tmp.name
        try:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Receipt image", ln=True)
            pdf.ln(2)
            # ширина страницы минус поля
            pdf.image(tmp_path, x=10, w=190)
        except Exception:
            logger.exception("Failed to embed receipt image into PDF")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    out = io.BytesIO()
    pdf.output(out)
    return out.getvalue()


def _save_receipt_pdf(tx_id: str, pdf_bytes: bytes) -> str:
    receipts_dir = os.path.join(UPLOAD_DIR, "receipts")
    os.makedirs(receipts_dir, exist_ok=True)
    safe = "".join(c for c in (tx_id or "order") if c.isalnum() or c in "-_")[:36] or "order"
    filename = f"receipt_{safe}.pdf"
    path = os.path.join(receipts_dir, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
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


def notify_player_receipt(order: dict) -> bool:
    """Шлёт PDF чека в личные сообщения на сайте. True если отправлено."""
    pdf_url = (order.get("receipt_pdf_url") or "").strip()
    if not pdf_url:
        return False
    if order.get("receipt_pm_sent"):
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
        # админ купил сам — всё равно покажем на странице, ЛС себе нельзя
        social_db.update_donation_order(order["transaction_id"], receipt_pm_sent=1)
        return True

    abs_pdf = _absolute_url(pdf_url)
    abs_print = _absolute_url(order.get("receipt_url") or pdf_url)
    amount = order.get("amount_rub") or 0
    name = order.get("tier_name") or "заказ"
    content = (
        f"Чек НПД по вашему донату «{name}» на {amount} ₽.\n\n"
        f"PDF: {abs_pdf}\n"
        f"Официальный чек: {abs_print}"
    )
    try:
        from app.services.messages import send_pm

        send_pm(sender_id, receiver_id, content, image_url=pdf_url)
        social_db.update_donation_order(order["transaction_id"], receipt_pm_sent=1)
        return True
    except Exception:
        logger.exception("Failed to send receipt PM for %s", order.get("transaction_id"))
        return False


async def _make_and_store_pdf(order: dict, *, print_url: str, receipt_uuid: str) -> str:
    print_bytes = None
    print_ctype = ""
    try:
        client = MoyNalogClient()
        print_bytes, print_ctype = await client.download_receipt_print(receipt_uuid)
        if print_ctype.lower().startswith("application/pdf") and print_bytes:
            return _save_receipt_pdf(order["transaction_id"], print_bytes)
    except Exception:
        logger.exception("Could not download NPD print form, building text PDF")

    pdf_bytes = _build_receipt_pdf(
        order=order,
        print_url=print_url,
        print_bytes=print_bytes,
        print_ctype=print_ctype,
    )
    return _save_receipt_pdf(order["transaction_id"], pdf_bytes)


async def issue_receipt_for_order(
    order: dict | None,
    *,
    force: bool = False,
) -> dict:
    """Создаёт чек в «Мой налог», PDF и ЛС игроку."""
    if not order:
        raise ValueError("Заказ не найден")
    tx_id = order.get("transaction_id") or ""
    if not tx_id:
        raise ValueError("Нет transaction_id")
    if order.get("status") != "confirmed":
        raise ValueError("Чек можно выдать только после подтверждения оплаты")

    if order.get("receipt_uuid") and not force:
        # дособираем PDF / ЛС, если чек уже есть
        if not order.get("receipt_pdf_url"):
            try:
                pdf_url = await _make_and_store_pdf(
                    order,
                    print_url=order.get("receipt_url") or "",
                    receipt_uuid=order["receipt_uuid"],
                )
                social_db.update_donation_order(tx_id, receipt_pdf_url=pdf_url)
                order = social_db.get_donation_order_by_tx(tx_id) or order
            except Exception:
                logger.exception("PDF rebuild failed for %s", tx_id)
        notify_player_receipt(order)
        return social_db.get_donation_order_by_tx(tx_id) or order

    if not nalog_configured():
        raise ValueError("Мой налог не настроен (NALOG_INN / NALOG_PASSWORD)")

    amount = float(order.get("amount_rub") or 0)
    if amount <= 0:
        raise ValueError("Нулевая сумма заказа")

    social_db.update_donation_order(
        tx_id,
        receipt_status="pending",
        receipt_error="",
    )

    op_time = None
    created = order.get("updated_at") or order.get("created_at")
    if created:
        try:
            raw = str(created).replace(" ", "T")
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            op_time = datetime.fromisoformat(raw)
            if op_time.tzinfo is None:
                op_time = op_time.replace(tzinfo=timezone.utc)
        except Exception:
            op_time = None

    try:
        client = MoyNalogClient()
        result = await client.create_income(
            name=receipt_service_title(order),
            amount_rub=amount,
            operation_time=op_time,
        )
        pdf_url = await _make_and_store_pdf(
            order,
            print_url=result["print_url"],
            receipt_uuid=result["uuid"],
        )
        social_db.update_donation_order(
            tx_id,
            receipt_uuid=result["uuid"],
            receipt_url=result["print_url"],
            receipt_pdf_url=pdf_url,
            receipt_status="issued",
            receipt_error="",
            receipt_issued_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            receipt_pm_sent=0,
        )
        logger.info(
            "NPD receipt issued tx=%s uuid=%s amount=%s pdf=%s",
            tx_id,
            result["uuid"],
            amount,
            pdf_url,
        )
    except MoyNalogError as e:
        social_db.update_donation_order(
            tx_id,
            receipt_status="error",
            receipt_error=(e.message or str(e))[:500],
        )
        raise ValueError(f"Ошибка Мой налог: {e.message}") from e
    except Exception as e:
        social_db.update_donation_order(
            tx_id,
            receipt_status="error",
            receipt_error=str(e)[:500],
        )
        raise

    order = social_db.get_donation_order_by_tx(tx_id) or order
    notify_player_receipt(order)
    return social_db.get_donation_order_by_tx(tx_id) or order


async def maybe_auto_issue_receipt(order: dict | None) -> dict | None:
    """Best-effort авто-чек после confirm, если включено."""
    if not order or not NALOG_AUTO_RECEIPT or not nalog_configured():
        return order
    if order.get("status") != "confirmed":
        return order
    try:
        return await issue_receipt_for_order(order)
    except Exception:
        logger.exception(
            "Auto NPD receipt failed for %s",
            order.get("transaction_id"),
        )
        return social_db.get_donation_order_by_tx(order["transaction_id"]) or order


def nalog_status_payload() -> dict[str, Any]:
    return {
        "configured": nalog_configured(),
        "auto_receipt": bool(NALOG_AUTO_RECEIPT),
        "tax_rate": float(NALOG_TAX_RATE or 0.04),
        "service_name_template": NALOG_SERVICE_NAME,
    }
