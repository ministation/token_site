"""Спонсорские тарифы и оплата через Platega.io."""
from __future__ import annotations

import json
import uuid
from typing import Any
from urllib.parse import quote

import aiohttp

import database_social as social_db
from app.config import (
    PLATEGA_API_BASE,
    PLATEGA_DEFAULT_METHOD,
    PLATEGA_MERCHANT_ID,
    PLATEGA_SECRET,
    SITE_PUBLIC_URL,
)

# Цены в рублях (месяц) — как на Boosty. Иконки — /static/icons/
DONATION_TIERS: dict[int, dict[str, Any]] = {
    1: {
        "id": 1,
        "name": "Унати",
        "price_rub": 290,
        "icon": "буст унати.png",
        "coins": 20,
        "perks": [
            "+20 монет в месяц",
            "Особая роль в сообществе Discord",
            "Зелёный цвет в ахелпе и ООС",
            "1 гарантированный вор или агент — 1 раз каждый день",
            "Пропуск на заполненный сервер",
        ],
    },
    2: {
        "id": 2,
        "name": "Космо-унати",
        "price_rub": 690,
        "icon": "космический унати.png",
        "coins": 30,
        "perks": [
            "+30 монет в месяц",
            "Особая роль в сообществе Discord",
            "Серебряный цвет в ахелпе и ООС",
            "Повышенный шанс ниндзя, дракона, абдукторов, нулевого заражённого или ревенанта",
            "1 гарантированный ниндзя, дракон, абдуктор, нулевой или ревенант — 1 раз каждый день",
            "Пропуск на заполненный сервер",
        ],
    },
    3: {
        "id": 3,
        "name": "Золотой унати",
        "price_rub": 1090,
        "icon": "золотой унати.png",
        "coins": 40,
        "featured": True,
        "perks": [
            "+40 монет в месяц",
            "Особая роль в сообществе Discord",
            "Жёлтый цвет в ахелпе и ООС",
            "Повышенный шанс ядерного оперативника, главы революции, космического культиста, дьявола или абдуктора",
            "1 гарантированный ядерный оперативник, глава революции, культист, дьявол или абдуктор — 1 раз каждый день",
            "Пропуск на заполненный сервер",
            "Все предыдущие привилегии",
        ],
    },
    4: {
        "id": 4,
        "name": "Магический унати",
        "price_rub": 1590,
        "icon": "магический унати.png",
        "coins": 60,
        "perks": [
            "+60 монет в месяц",
            "Особая роль в сообществе Discord",
            "Фиолетовый цвет в ахелпе и ООС",
            "Повышенный шанс блоба, шедоулинга, мага, генокрада, еретика, фантома, демона резни, мясника и других крупных антагонистов",
            "1 гарантированный крупный антагонист — 1 раз каждый день",
            "Пропуск на заполненный сервер",
            "Все предыдущие привилегии",
        ],
    },
    5: {
        "id": 5,
        "name": "Гига-унати",
        "price_rub": 2990,
        "icon": "гига унати.png",
        "coins": 100,
        "perks": [
            "+100 монет в месяц",
            "Для спонсоров и меценатов проекта",
            "Особая роль в сообществе Discord",
            "Оранжевый цвет в ахелпе и ООС",
            "Допуск к участию в собраниях совета Мини-станции",
            "Ваши предложения к разработке учитываются в первую очередь",
            "Все предыдущие привилегии",
        ],
    },
}

PAYMENT_METHODS = [
    {
        "id": 2,
        "label": "СБП / QR",
        "hint": "Быстрый перевод через СБП",
        "icon": "/static/payment/sbp.svg",
    },
    {
        "id": 10,
        "label": "Карта МИР",
        "hint": "Банковская карта РФ",
        "icon": "/static/payment/mir.svg",
    },
    {
        "id": 12,
        "label": "Международная карта",
        "hint": "Visa / Mastercard",
        "icon": "/static/payment/card-intl.svg",
    },
]


def platega_configured() -> bool:
    return bool(PLATEGA_MERCHANT_ID and PLATEGA_SECRET)


def icon_url(filename: str) -> str:
    return f"/static/icons/{quote(filename)}"


def serialize_tier(tier: dict) -> dict:
    return {
        "id": tier["id"],
        "name": tier["name"],
        "price_rub": tier["price_rub"],
        "price_label": f"{tier['price_rub']:,} ₽".replace(",", " "),
        "period": "мес",
        "icon": icon_url(tier["icon"]),
        "coins": tier.get("coins"),
        "featured": bool(tier.get("featured")),
        "perks": list(tier.get("perks") or []),
    }


def list_tiers() -> list[dict]:
    return [serialize_tier(DONATION_TIERS[i]) for i in sorted(DONATION_TIERS)]


def get_tier(tier_id: int) -> dict | None:
    tier = DONATION_TIERS.get(int(tier_id))
    return serialize_tier(tier) if tier else None


def _platega_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET,
    }


async def create_payment(
    *,
    tier_id: int,
    payment_method: int | None = None,
    player_id: str | None = None,
    discord_id: str | None = None,
    contact: str | None = None,
) -> dict:
    if not platega_configured():
        raise ValueError("Платежи пока не подключены: укажите PLATEGA_MERCHANT_ID и PLATEGA_SECRET")

    raw = DONATION_TIERS.get(int(tier_id))
    if not raw:
        raise ValueError("Неизвестный тариф")

    method = int(payment_method or PLATEGA_DEFAULT_METHOD)
    if method not in {m["id"] for m in PAYMENT_METHODS}:
        raise ValueError("Недоступный способ оплаты")

    tx_id = str(uuid.uuid4())
    return_url = f"{SITE_PUBLIC_URL}/#/donate?order={tx_id}&result=success"
    fail_url = f"{SITE_PUBLIC_URL}/#/donate?order={tx_id}&result=fail"
    payload = json.dumps({"tier_id": raw["id"], "player_id": player_id or ""}, ensure_ascii=False)

    social_db.create_donation_order(
        transaction_id=tx_id,
        tier_id=raw["id"],
        tier_name=raw["name"],
        amount_rub=raw["price_rub"],
        payment_method=method,
        player_id=player_id,
        discord_id=discord_id,
        contact=contact,
        payload=payload,
    )

    body = {
        "paymentMethod": method,
        "id": tx_id,
        "paymentDetails": {
            "amount": raw["price_rub"],
            "currency": "RUB",
        },
        "description": f"Мини-станция · {raw['name']} (мес.)",
        "return": return_url,
        "failedUrl": fail_url,
        "payload": payload,
    }

    url = f"{PLATEGA_API_BASE}/transaction/process"
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=_platega_headers(), json=body) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 400:
                msg = data.get("message") if isinstance(data, dict) else None
                social_db.update_donation_order(tx_id, status="failed", raw_callback=json.dumps(data, ensure_ascii=False))
                raise ValueError(msg or f"Ошибка Platega ({resp.status})")

    redirect = (data or {}).get("redirect")
    if redirect:
        social_db.update_donation_order(tx_id, redirect_url=redirect)
    return {
        "transaction_id": (data or {}).get("transactionId") or tx_id,
        "redirect": redirect,
        "status": (data or {}).get("status") or "PENDING",
        "expires_in": (data or {}).get("expiresIn"),
        "tier": serialize_tier(raw),
        "amount_rub": raw["price_rub"],
    }


async def fetch_payment_status(transaction_id: str) -> dict:
    if not platega_configured():
        raise ValueError("Platega не настроена")
    url = f"{PLATEGA_API_BASE}/transaction/{transaction_id}"
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=_platega_headers()) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 400:
                raise ValueError((data or {}).get("message") or f"Ошибка статуса ({resp.status})")
            return data if isinstance(data, dict) else {"raw": data}


def apply_callback(payload: dict) -> dict:
    tx_id = str(payload.get("id") or "")
    status_raw = str(payload.get("status") or "").upper()
    if not tx_id:
        raise ValueError("Нет id транзакции")

    status_map = {
        "CONFIRMED": "confirmed",
        "CANCELED": "canceled",
        "CANCELLED": "canceled",
        "PENDING": "pending",
        "CHARGEBACKED": "chargebacked",
    }
    status = status_map.get(status_raw, status_raw.lower() or "pending")
    social_db.update_donation_order(
        tx_id,
        status=status,
        raw_callback=json.dumps(payload, ensure_ascii=False),
    )
    order = social_db.get_donation_order_by_tx(tx_id)
    return {"ok": True, "transaction_id": tx_id, "status": status, "order": order}


def catalog_payload() -> dict:
    return {
        "configured": platega_configured(),
        "currency": "RUB",
        "tiers": list_tiers(),
        "methods": PAYMENT_METHODS,
        "default_method": PLATEGA_DEFAULT_METHOD,
    }
