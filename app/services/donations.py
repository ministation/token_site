"""Спонсорские тарифы, пакеты монет и ручная оплата СБП."""
from __future__ import annotations

import json
import uuid
from typing import Any
from urllib.parse import quote

import aiohttp

import database_social as social_db
from app.config import (
    DONATION_NOTIFY_EMAIL,
    MANUAL_SBP_ENABLED,
    PLATEGA_API_BASE,
    PLATEGA_DEFAULT_METHOD,
    PLATEGA_MERCHANT_ID,
    PLATEGA_SECRET,
    SBP_PAY_LINK,
    SBP_QR_PATH,
    SITE_PUBLIC_URL,
    SPONSORSHIP_DAYS,
)
from app.services.bank import add_tokens
from app.services.mail import send_email, smtp_configured

# Цены в рублях (месяц). Иконки - /static/icons/
DONATION_TIERS: dict[int, dict[str, Any]] = {
    1: {
        "id": 1,
        "name": "Унати",
        "price_rub": 290,
        "icon": "унати.png",
        "coins": 20,
        "perks": [
            "Особая роль в сообществе Discord",
            "Зелёный цвет в ахелпе и ООС",
            "1 гарантированный вор или агент - 1 раз каждый день",
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
            "Особая роль в сообществе Discord",
            "Серебряный цвет в ахелпе и ООС",
            "Повышенный шанс ниндзя, дракона, абдукторов, нулевого заражённого или ревенанта",
            "1 гарантированный ниндзя, дракон, абдуктор, нулевой или ревенант - 1 раз каждый день",
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
            "Особая роль в сообществе Discord",
            "Жёлтый цвет в ахелпе и ООС",
            "Повышенный шанс ядерного оперативника, главы революции, космического культиста, дьявола или абдуктора",
            "1 гарантированный ядерный оперативник, глава революции, культист, дьявол или абдуктор - 1 раз каждый день",
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
            "Особая роль в сообществе Discord",
            "Фиолетовый цвет в ахелпе и ООС",
            "Повышенный шанс блоба, шедоулинга, мага, генокрада, еретика, фантома, демона резни, мясника и других крупных антагонистов",
            "1 гарантированный крупный антагонист - 1 раз каждый день",
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
            "Для спонсоров и меценатов проекта",
            "Особая роль в сообществе Discord",
            "Оранжевый цвет в ахелпе и ООС",
            "Допуск к участию в собраниях совета Мини-станции",
            "Ваши предложения к разработке учитываются в первую очередь",
            "Все предыдущие привилегии",
        ],
    },
}

COIN_PACKS: dict[int, dict[str, Any]] = {
    1: {"id": 1, "name": "Рюкзак монет", "coins": 20, "price_rub": 190, "badge": None},
    2: {"id": 2, "name": "Тулбокс монет", "coins": 50, "price_rub": 490, "badge": None},
    3: {"id": 3, "name": "Ящик монет", "coins": 100, "price_rub": 890, "badge": "Выгодно", "featured": True},
    4: {"id": 4, "name": "Сейф монет", "coins": 200, "price_rub": 1690, "badge": "−30%"},
    5: {"id": 5, "name": "Ящик суперприпасов монет", "coins": 300, "price_rub": 2490, "badge": "−31%"},
}

_COIN_BASE_RATE = 12.0

PAYMENT_METHODS = [
    {
        "id": 2,
        "label": "СБП",
        "hint": "Оплата по QR",
        "icon": "/static/payment/sbp.png",
    },
]


def platega_configured() -> bool:
    return bool(PLATEGA_MERCHANT_ID and PLATEGA_SECRET)


def payments_available() -> bool:
    return bool(MANUAL_SBP_ENABLED) or platega_configured()


def icon_url(filename: str) -> str:
    return f"/static/icons/{quote(filename)}"


def _rub_label(amount: int) -> str:
    return f"{amount:,} ₽".replace(",", " ")


def serialize_tier(tier: dict) -> dict:
    return {
        "id": tier["id"],
        "name": tier["name"],
        "price_rub": tier["price_rub"],
        "price_label": _rub_label(tier["price_rub"]),
        "period": "мес",
        "icon": icon_url(tier["icon"]),
        "coins": tier.get("coins"),
        "featured": bool(tier.get("featured")),
        "perks": list(tier.get("perks") or []),
    }


def serialize_coin_pack(pack: dict) -> dict:
    coins = int(pack["coins"])
    price = int(pack["price_rub"])
    per = price / coins if coins else 0
    discount = max(0, int(round((1 - per / _COIN_BASE_RATE) * 100))) if _COIN_BASE_RATE else 0
    return {
        "id": pack["id"],
        "name": pack["name"],
        "coins": coins,
        "price_rub": price,
        "price_label": _rub_label(price),
        "unit_price": round(per, 2),
        "unit_label": f"{per:.2f} ₽/шт".replace(".", ","),
        "discount_pct": discount,
        "badge": pack.get("badge"),
        "featured": bool(pack.get("featured")),
    }


def list_tiers() -> list[dict]:
    return [serialize_tier(DONATION_TIERS[i]) for i in sorted(DONATION_TIERS)]


def list_coin_packs() -> list[dict]:
    return [serialize_coin_pack(COIN_PACKS[i]) for i in sorted(COIN_PACKS)]


def get_tier(tier_id: int) -> dict | None:
    tier = DONATION_TIERS.get(int(tier_id))
    return serialize_tier(tier) if tier else None


def get_coin_pack(pack_id: int) -> dict | None:
    pack = COIN_PACKS.get(int(pack_id))
    return serialize_coin_pack(pack) if pack else None


def _platega_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET,
    }


def _resolve_game_uuid(user: dict | None) -> str | None:
    if not user:
        return None
    player = user.get("player") or {}
    uuid_val = player.get("user_uuid") or (user.get("social") or {}).get("user_uuid")
    if uuid_val and not str(uuid_val).startswith("discord_"):
        return str(uuid_val)
    return None


def _build_product(
    *,
    product_type: str,
    tier_id: int | None,
    pack_id: int | None,
    game_user_uuid: str | None,
) -> tuple[str, int, str, int, dict]:
    product_type = (product_type or "tier").strip().lower()
    coins_amount = 0
    if product_type == "coins":
        raw_pack = COIN_PACKS.get(int(pack_id or 0))
        if not raw_pack:
            raise ValueError("Неизвестный пакет монет")
        if not game_user_uuid:
            raise ValueError("Для покупки монет войдите через Discord с привязанным игровым аккаунтом")
        amount_rub = raw_pack["price_rub"]
        tier_db_id = int(raw_pack["id"])
        tier_name = f"Монетки · {raw_pack['coins']}"
        coins_amount = int(raw_pack["coins"])
        serialized = serialize_coin_pack(raw_pack)
    elif product_type == "tier":
        raw = DONATION_TIERS.get(int(tier_id or 0))
        if not raw:
            raise ValueError("Неизвестный тариф")
        amount_rub = raw["price_rub"]
        tier_db_id = int(raw["id"])
        tier_name = raw["name"]
        coins_amount = int(raw.get("coins") or 0)
        serialized = serialize_tier(raw)
    else:
        raise ValueError("Неизвестный тип товара")
    return product_type, tier_db_id, tier_name, coins_amount, amount_rub, serialized  # type: wrong


# Fix return type - I made a mistake with tuple unpacking. Let me rewrite create_payment cleanly.
