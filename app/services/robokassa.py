"""Хелперы Robokassa: подпись, параметры оплаты, проверка Result URL."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import quote, urlencode

from app.config import (
    ROBOKASSA_HASH,
    ROBOKASSA_IS_TEST,
    ROBOKASSA_LOGIN,
    ROBOKASSA_PASSWORD1,
    ROBOKASSA_PASSWORD2,
    ROBOKASSA_PAYMENT_URL,
    ROBOKASSA_RECEIPT_ENABLED,
    ROBOKASSA_RECEIPT_TAX,
    ROBOKASSA_TEST_PASSWORD1,
    ROBOKASSA_TEST_PASSWORD2,
)


def configured() -> bool:
    login = ROBOKASSA_LOGIN
    p1, p2 = _passwords()
    return bool(login and p1 and p2)


def _passwords() -> tuple[str, str]:
    if ROBOKASSA_IS_TEST:
        p1 = ROBOKASSA_TEST_PASSWORD1 or ROBOKASSA_PASSWORD1
        p2 = ROBOKASSA_TEST_PASSWORD2 or ROBOKASSA_PASSWORD2
        return p1, p2
    return ROBOKASSA_PASSWORD1, ROBOKASSA_PASSWORD2


def _digest(payload: str) -> str:
    algo = (ROBOKASSA_HASH or "md5").lower()
    data = payload.encode("utf-8")
    if algo in ("sha256", "sha-256"):
        return hashlib.sha256(data).hexdigest()
    if algo in ("sha512", "sha-512"):
        return hashlib.sha512(data).hexdigest()
    if algo in ("sha384", "sha-384"):
        return hashlib.sha384(data).hexdigest()
    return hashlib.md5(data).hexdigest()


def format_out_sum(amount_rub: int | float | str) -> str:
    """Сумма в формате Robokassa (точка, 2 знака)."""
    return f"{float(amount_rub):.2f}"


def _clean_item_name(name: str) -> str:
    """Имя позиции чека без спецсимволов (требование Robokassa)."""
    text = re.sub(r"[^\w\s\-.,()/]+", " ", (name or "Usluga"), flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return (text or "Usluga")[:128]


def build_receipt(*, description: str, amount_rub: int | float) -> str:
    """JSON чека 54-ФЗ (одна позиция — услуга). ensure_ascii для стабильной подписи."""
    total = round(float(amount_rub), 2)
    payload = {
        "items": [
            {
                "name": _clean_item_name(description),
                "quantity": 1,
                "sum": total,
                "payment_method": "full_payment",
                "payment_object": "service",
                "tax": ROBOKASSA_RECEIPT_TAX,
            }
        ]
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def sign_payment(
    *,
    out_sum: str,
    inv_id: int | str,
    receipt_json: str | None = None,
    shp: dict[str, str] | None = None,
) -> str:
    """Подпись инициализации: Login:OutSum:InvId[:Receipt]:Pass1[:Shp_…]"""
    login = ROBOKASSA_LOGIN
    password1, _ = _passwords()
    parts = [login, out_sum, str(inv_id)]
    if receipt_json:
        parts.append(quote(receipt_json, safe=""))
    parts.append(password1)
    if shp:
        for key in sorted(shp.keys()):
            parts.append(f"{key}={shp[key]}")
    return _digest(":".join(parts))


def sign_result(
    *,
    out_sum: str,
    inv_id: int | str,
    shp: dict[str, str] | None = None,
) -> str:
    """Подпись Result URL: OutSum:InvId:Pass2[:Shp_…]"""
    _, password2 = _passwords()
    parts = [out_sum, str(inv_id), password2]
    if shp:
        for key in sorted(shp.keys()):
            parts.append(f"{key}={shp[key]}")
    return _digest(":".join(parts))


def extract_shp(params: dict[str, Any]) -> dict[str, str]:
    """Собирает Shp_* параметры (нормализует префикс к Shp_)."""
    out: dict[str, str] = {}
    for key, value in params.items():
        k = str(key)
        if k.lower().startswith("shp_"):
            out["Shp_" + k[4:]] = str(value)
    return out


def build_payment_params(
    *,
    amount_rub: int | float,
    inv_id: int,
    description: str,
    email: str | None = None,
    include_receipt: bool | None = None,
    shp: dict[str, str] | None = None,
) -> dict[str, str]:
    """Параметры для POST-формы на Robokassa (предпочтительно при Receipt)."""
    out_sum = format_out_sum(amount_rub)
    use_receipt = ROBOKASSA_RECEIPT_ENABLED if include_receipt is None else include_receipt
    receipt = build_receipt(description=description, amount_rub=amount_rub) if use_receipt else None
    signature = sign_payment(
        out_sum=out_sum,
        inv_id=inv_id,
        receipt_json=receipt,
        shp=shp,
    )
    params: dict[str, str] = {
        "MerchantLogin": ROBOKASSA_LOGIN,
        "OutSum": out_sum,
        "InvId": str(inv_id),
        "Description": _clean_item_name(description)[:100],
        "SignatureValue": signature,
        "Culture": "ru",
        "Encoding": "utf-8",
    }
    if receipt:
        # В форму — сырой JSON; браузер/клиент закодирует один раз.
        # В подпись уже ушёл quote(receipt).
        params["Receipt"] = receipt
    if email:
        params["Email"] = email.strip()[:64]
    if ROBOKASSA_IS_TEST:
        params["IsTest"] = "1"
    if shp:
        params.update(shp)
    return params


def build_payment_url(
    *,
    amount_rub: int | float,
    inv_id: int,
    description: str,
    email: str | None = None,
    include_receipt: bool | None = None,
    shp: dict[str, str] | None = None,
) -> str:
    params = build_payment_params(
        amount_rub=amount_rub,
        inv_id=inv_id,
        description=description,
        email=email,
        include_receipt=include_receipt,
        shp=shp,
    )
    return f"{ROBOKASSA_PAYMENT_URL}?{urlencode(params)}"


def payment_endpoint() -> str:
    return ROBOKASSA_PAYMENT_URL


def verify_result_signature(
    *,
    out_sum: str,
    inv_id: int | str,
    signature_value: str,
    shp: dict[str, str] | None = None,
) -> bool:
    expected = sign_result(out_sum=out_sum, inv_id=inv_id, shp=shp)
    return expected.lower() == (signature_value or "").strip().lower()
