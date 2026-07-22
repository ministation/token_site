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
)
from app.db.database import get_pg_pool
from app.services import robokassa
from app.services.bank import add_tokens
from app.services.mail import send_email, smtp_configured


async def upsert_discord_sponsor(discord_id: str | int, sponsor_level: int) -> dict:
    """Пишет/обновляет спонсора в игровой Postgres-таблице discord_sponsor.
    Уровень не понижается, если уже есть более высокий.
    """
    did = int(str(discord_id).strip())
    level = max(1, min(int(sponsor_level), 5))
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, sponsor_level FROM discord_sponsor WHERE discord_id = $1::bigint",
            did,
        )
        if row:
            new_level = max(int(row["sponsor_level"] or 0), level)
            await conn.execute(
                "UPDATE discord_sponsor SET sponsor_level = $1 WHERE discord_id = $2::bigint",
                new_level,
                did,
            )
            return {"discord_id": str(did), "sponsor_level": new_level, "updated": True}
        await conn.execute(
            "INSERT INTO discord_sponsor (discord_id, sponsor_level) VALUES ($1::bigint, $2)",
            did,
            level,
        )
        return {"discord_id": str(did), "sponsor_level": level, "updated": False}

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
    {
        "id": 11,
        "label": "МИР",
        "hint": "Карта МИР / RUB",
        "icon": "/static/payment/mir.png",
    },
]

# Старые id из UI/доков → актуальные коды Platega
_PLATEGA_METHOD_ALIASES = {
    10: 11,  # устаревший CardRu → карточный эквайринг
}


def platega_configured() -> bool:
    return bool(PLATEGA_MERCHANT_ID and PLATEGA_SECRET)


def robokassa_configured() -> bool:
    return robokassa.configured()


def payments_available() -> bool:
    return platega_configured() or robokassa_configured() or bool(MANUAL_SBP_ENABLED)


def payment_mode() -> str:
    # Приоритет: Platega → Robokassa → ручной СБП
    if platega_configured():
        return "platega"
    if robokassa_configured():
        return "robokassa"
    if MANUAL_SBP_ENABLED:
        return "manual_sbp"
    return "off"


def icon_url(filename: str) -> str:
    return f"/static/icons/{quote(filename)}"


def _rub_label(amount: int) -> str:
    return f"{amount:,} ₽".replace(",", " ")


def serialize_discount(row: dict) -> dict:
    percent = max(1, min(int(row.get("percent") or 0), 90))
    return {
        "id": row["id"],
        "title": row.get("title") or "Скидка",
        "percent": percent,
        "scope": row.get("scope") or "all",
        "target_id": row.get("target_id"),
        "badge_text": row.get("badge_text") or f"−{percent}%",
        "starts_at": row.get("starts_at"),
        "ends_at": row.get("ends_at"),
        "active": bool(row.get("active")),
        "created_by": row.get("created_by"),
        "created_at": row.get("created_at"),
    }


def _discount_matches(d: dict, product_type: str, product_id: int) -> bool:
    scope = (d.get("scope") or "all").strip().lower()
    tid = d.get("target_id")
    if scope == "all":
        return True
    if scope == "tiers" and product_type == "tier":
        return True
    if scope == "coins" and product_type == "coins":
        return True
    if scope == "tier" and product_type == "tier" and tid is not None and int(tid) == int(product_id):
        return True
    if scope in ("pack", "coins_pack") and product_type == "coins" and tid is not None and int(tid) == int(product_id):
        return True
    return False


def best_discount_for(product_type: str, product_id: int, discounts: list[dict] | None = None) -> dict | None:
    rows = discounts if discounts is not None else social_db.get_active_donation_discounts()
    best = None
    for raw in rows:
        d = serialize_discount(raw) if "percent" in raw and "title" in raw else raw
        if not _discount_matches(d, product_type, product_id):
            continue
        if best is None or int(d["percent"]) > int(best["percent"]):
            best = d
    return best


def apply_price_discount(base_price: int, percent: int) -> int:
    base = max(0, int(base_price))
    pct = max(0, min(int(percent), 90))
    if pct <= 0:
        return base
    # минимум 1 ₽ если база > 0
    discounted = int(round(base * (100 - pct) / 100.0))
    if base > 0:
        return max(1, discounted)
    return 0


def serialize_tier(tier: dict, discounts: list[dict] | None = None) -> dict:
    base = int(tier["price_rub"])
    disc = best_discount_for("tier", int(tier["id"]), discounts)
    price = apply_price_discount(base, disc["percent"]) if disc else base
    out = {
        "id": tier["id"],
        "name": tier["name"],
        "price_rub": price,
        "price_label": _rub_label(price),
        "base_price_rub": base,
        "base_price_label": _rub_label(base),
        "period": "мес",
        "icon": icon_url(tier["icon"]),
        "coins": tier.get("coins"),
        "featured": bool(tier.get("featured")),
        "perks": list(tier.get("perks") or []),
        "discount": disc,
        "on_sale": bool(disc),
    }
    return out


def serialize_coin_pack(pack: dict, discounts: list[dict] | None = None) -> dict:
    coins = int(pack["coins"])
    base = int(pack["price_rub"])
    disc = best_discount_for("coins", int(pack["id"]), discounts)
    price = apply_price_discount(base, disc["percent"]) if disc else base
    per = price / coins if coins else 0
    unit_discount = max(0, int(round((1 - per / _COIN_BASE_RATE) * 100))) if _COIN_BASE_RATE else 0
    return {
        "id": pack["id"],
        "name": pack["name"],
        "coins": coins,
        "price_rub": price,
        "price_label": _rub_label(price),
        "base_price_rub": base,
        "base_price_label": _rub_label(base),
        "unit_price": round(per, 2),
        "unit_label": f"{per:.2f} ₽/шт".replace(".", ","),
        "discount_pct": unit_discount,
        "badge": pack.get("badge"),
        "featured": bool(pack.get("featured")),
        "discount": disc,
        "on_sale": bool(disc),
    }


def list_tiers(discounts: list[dict] | None = None) -> list[dict]:
    active = discounts if discounts is not None else social_db.get_active_donation_discounts()
    active_s = [serialize_discount(d) for d in active]
    return [serialize_tier(DONATION_TIERS[i], active_s) for i in sorted(DONATION_TIERS)]


def list_coin_packs(discounts: list[dict] | None = None) -> list[dict]:
    active = discounts if discounts is not None else social_db.get_active_donation_discounts()
    active_s = [serialize_discount(d) for d in active]
    return [serialize_coin_pack(COIN_PACKS[i], active_s) for i in sorted(COIN_PACKS)]


def active_promo_summary() -> dict | None:
    """Лучшая текущая акция для бейджа на кнопке «Донат»."""
    rows = [serialize_discount(d) for d in social_db.get_active_donation_discounts()]
    if not rows:
        return None
    best = max(rows, key=lambda d: int(d["percent"]))
    # ближайший конец среди активных
    ends = [d.get("ends_at") for d in rows if d.get("ends_at")]
    return {
        "has_sale": True,
        "percent": best["percent"],
        "badge_text": best.get("badge_text") or f"−{best['percent']}%",
        "title": best.get("title"),
        "ends_at": min(ends) if ends else best.get("ends_at"),
        "count": len(rows),
        "discounts": rows,
    }


def _platega_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET,
    }


async def create_platega_transaction(
    *,
    transaction_id: str,
    amount_rub: int,
    description: str,
    payment_method: int,
    payload: str | None = None,
) -> dict:
    """POST /transaction/process → redirect URL."""
    method = int(payment_method or PLATEGA_DEFAULT_METHOD or 2)
    method = int(_PLATEGA_METHOD_ALIASES.get(method, method))
    allowed = {m["id"] for m in PAYMENT_METHODS}
    if method not in allowed:
        method = int(PLATEGA_DEFAULT_METHOD or 2)
        method = int(_PLATEGA_METHOD_ALIASES.get(method, method))
        if method not in allowed:
            method = 2
    return_url = f"{SITE_PUBLIC_URL}/donate?order={transaction_id}&paid=1&result=success"
    fail_url = f"{SITE_PUBLIC_URL}/donate?order={transaction_id}&paid=0&result=fail"
    body = {
        "paymentMethod": method,
        "id": transaction_id,
        "paymentDetails": {
            "amount": int(amount_rub),
            "currency": "RUB",
        },
        "description": (description or "Мини-станция")[:200],
        "return": return_url,
        "failedUrl": fail_url,
        "payload": payload or transaction_id,
    }
    url = f"{PLATEGA_API_BASE}/transaction/process"
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=_platega_headers(), json=body) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 400:
                msg = None
                if isinstance(data, dict):
                    msg = data.get("message") or data.get("Message") or data.get("error")
                raise ValueError(msg or f"Platega ошибка ({resp.status})")
            if not isinstance(data, dict):
                raise ValueError("Некорректный ответ Platega")
            redirect = (
                data.get("redirect")
                or data.get("Redirect")
                or data.get("url")
                or data.get("Url")
            )
            if not redirect:
                raise ValueError("Platega не вернула ссылку на оплату")
            data["redirect"] = redirect
            data["_paymentMethodSent"] = method
            return data


def _resolve_game_uuid(user: dict | None) -> str | None:
    if not user:
        return None
    player = user.get("player") or {}
    uuid_val = player.get("user_uuid") or (user.get("social") or {}).get("user_uuid")
    if uuid_val and not str(uuid_val).startswith("discord_"):
        return str(uuid_val)
    return None


def _prepare_product(
    *,
    product_type: str,
    tier_id: int | None,
    pack_id: int | None,
    game_user_uuid: str | None,
) -> dict:
    product_type = (product_type or "tier").strip().lower()
    active = [serialize_discount(d) for d in social_db.get_active_donation_discounts()]
    if product_type == "coins":
        raw_pack = COIN_PACKS.get(int(pack_id or 0))
        if not raw_pack:
            raise ValueError("Неизвестный пакет монет")
        if not game_user_uuid:
            raise ValueError("Для покупки монет войдите через Discord с привязанным игровым аккаунтом")
        item = serialize_coin_pack(raw_pack, active)
        return {
            "product_type": "coins",
            "tier_db_id": int(raw_pack["id"]),
            "tier_name": f"Монетки · {raw_pack['coins']}",
            "coins_amount": int(raw_pack["coins"]),
            "amount_rub": int(item["price_rub"]),
            "base_amount_rub": int(item["base_price_rub"]),
            "discount": item.get("discount"),
            "description": f"Мини-станция · {raw_pack['coins']} монет",
            "item": item,
        }
    if product_type == "tier":
        raw = DONATION_TIERS.get(int(tier_id or 0))
        if not raw:
            raise ValueError("Неизвестный тариф")
        item = serialize_tier(raw, active)
        return {
            "product_type": "tier",
            "tier_db_id": int(raw["id"]),
            "tier_name": raw["name"],
            "coins_amount": int(raw.get("coins") or 0),
            "amount_rub": int(item["price_rub"]),
            "base_amount_rub": int(item["base_price_rub"]),
            "discount": item.get("discount"),
            "description": f"Мини-станция · {raw['name']} (мес.)",
            "item": item,
        }
    raise ValueError("Неизвестный тип товара")


def sbp_payment_info(amount_rub: int | None = None) -> dict:
    return {
        "link": SBP_PAY_LINK,
        "qr": SBP_QR_PATH,
        "amount_rub": amount_rub,
        "amount_label": _rub_label(amount_rub) if amount_rub is not None else None,
        "hint": "Отсканируйте QR в банковском приложении или откройте ссылку СБП. В комментарии укажите номер заказа.",
    }


async def create_payment(
    *,
    product_type: str = "tier",
    tier_id: int | None = None,
    pack_id: int | None = None,
    payment_method: int | None = None,
    player_id: str | None = None,
    discord_id: str | None = None,
    game_user_uuid: str | None = None,
    contact: str | None = None,
) -> dict:
    if not payments_available():
        raise ValueError("Платежи временно недоступны")

    mode = payment_mode()
    method = int(payment_method or PLATEGA_DEFAULT_METHOD or 2)
    method = int(_PLATEGA_METHOD_ALIASES.get(method, method))
    if method not in {m["id"] for m in PAYMENT_METHODS}:
        method = int(PLATEGA_DEFAULT_METHOD or 2)
        method = int(_PLATEGA_METHOD_ALIASES.get(method, method))
        if method not in {m["id"] for m in PAYMENT_METHODS}:
            method = 2

    prepared = _prepare_product(
        product_type=product_type,
        tier_id=tier_id,
        pack_id=pack_id,
        game_user_uuid=game_user_uuid,
    )
    product_type = prepared["product_type"]
    amount_rub = prepared["amount_rub"]
    tier_db_id = prepared["tier_db_id"]
    tier_name = prepared["tier_name"]
    coins_amount = prepared["coins_amount"]
    serialized = prepared["item"]
    description = prepared["description"]

    if product_type == "tier" and not discord_id:
        raise ValueError("Для покупки подписки войдите через Discord")

    tx_id = str(uuid.uuid4())
    payload = json.dumps(
        {
            "product_type": product_type,
            "tier_id": tier_id,
            "pack_id": pack_id,
            "player_id": player_id or "",
            "game_user_uuid": game_user_uuid or "",
            "coins_amount": coins_amount,
            "mode": mode,
            "payment_method": method,
            "base_amount_rub": prepared.get("base_amount_rub"),
            "discount": prepared.get("discount"),
        },
        ensure_ascii=False,
    )

    if mode == "platega":
        social_db.create_donation_order(
            transaction_id=tx_id,
            tier_id=tier_db_id,
            tier_name=tier_name,
            amount_rub=amount_rub,
            payment_method=method,
            player_id=player_id,
            discord_id=discord_id,
            contact=contact,
            payload=payload,
            product_type=product_type,
            coins_amount=coins_amount,
            game_user_uuid=game_user_uuid,
        )
        try:
            remote = await create_platega_transaction(
                transaction_id=tx_id,
                amount_rub=amount_rub,
                description=description,
                payment_method=method,
                payload=tx_id,
            )
        except Exception:
            social_db.update_donation_order(tx_id, status="failed")
            raise
        redirect = remote.get("redirect") or remote.get("Redirect")
        social_db.update_donation_order(
            tx_id,
            redirect_url=redirect,
            raw_callback=json.dumps({"platega_create": remote}, ensure_ascii=False),
        )
        return {
            "transaction_id": tx_id,
            "mode": "platega",
            "status": "pending",
            "product_type": product_type,
            "item": serialized,
            "tier_name": tier_name,
            "amount_rub": amount_rub,
            "amount_label": _rub_label(amount_rub),
            "redirect": redirect,
            "remote": remote,
            "wait_path": f"/donate?order={tx_id}&wait=1",
        }

    if mode == "robokassa":
        order = social_db.create_donation_order(
            transaction_id=tx_id,
            tier_id=tier_db_id,
            tier_name=tier_name,
            amount_rub=amount_rub,
            payment_method=method,
            player_id=player_id,
            discord_id=discord_id,
            contact=contact,
            payload=payload,
            product_type=product_type,
            coins_amount=coins_amount,
            game_user_uuid=game_user_uuid,
        )
        inv_id = int(order["id"])
        shp = {"Shp_tx": tx_id}
        pay_params = robokassa.build_payment_params(
            amount_rub=amount_rub,
            inv_id=inv_id,
            description=description,
            email=None,
            include_receipt=None,
            shp=shp,
        )
        pay_url = f"/api/donations/robokassa/pay/{tx_id}"
        meta = json.loads(payload)
        meta["robokassa_pay"] = pay_params
        meta["robokassa_endpoint"] = robokassa.payment_endpoint()
        social_db.update_donation_order(
            tx_id,
            redirect_url=pay_url,
            payload=json.dumps(meta, ensure_ascii=False),
        )
        return {
            "transaction_id": tx_id,
            "inv_id": inv_id,
            "mode": "robokassa",
            "status": "pending",
            "product_type": product_type,
            "item": serialized,
            "tier_name": tier_name,
            "amount_rub": amount_rub,
            "amount_label": _rub_label(amount_rub),
            "redirect": pay_url,
            "pay_path": pay_url,
            "wait_path": f"/donate?order={tx_id}&wait=1",
        }

    # Ручной СБП (QR + подтверждение админом) — запасной режим
    social_db.create_donation_order(
        transaction_id=tx_id,
        tier_id=tier_db_id,
        tier_name=tier_name,
        amount_rub=amount_rub,
        payment_method=2,
        player_id=player_id,
        discord_id=discord_id,
        contact=contact,
        payload=payload,
        product_type=product_type,
        coins_amount=coins_amount,
        game_user_uuid=game_user_uuid,
        redirect_url=SBP_PAY_LINK,
    )
    return {
        "transaction_id": tx_id,
        "mode": "manual_sbp",
        "status": "pending",
        "product_type": product_type,
        "item": serialized,
        "tier_name": tier_name,
        "amount_rub": amount_rub,
        "amount_label": _rub_label(amount_rub),
        "sbp": sbp_payment_info(amount_rub),
        "redirect": None,
        "wait_path": f"/donate?order={tx_id}&wait=1",
    }


async def apply_robokassa_result(params: dict[str, Any]) -> str:
    """Обрабатывает Result URL. Возвращает тело ответа OK{InvId} или ошибку."""
    out_sum = str(params.get("OutSum") or params.get("out_sum") or "").strip()
    inv_raw = params.get("InvId") or params.get("inv_id") or ""
    signature = str(params.get("SignatureValue") or params.get("signaturevalue") or "").strip()
    if not out_sum or inv_raw in ("", None) or not signature:
        raise ValueError("Неполные параметры Robokassa")

    try:
        inv_id = int(inv_raw)
    except (TypeError, ValueError) as e:
        raise ValueError("Некорректный InvId") from e

    shp = robokassa.extract_shp(params)
    if not robokassa.verify_result_signature(
        out_sum=out_sum,
        inv_id=inv_id,
        signature_value=signature,
        shp=shp or None,
    ):
        raise ValueError("Неверная подпись Robokassa")

    order = social_db.get_donation_order_by_id(inv_id)
    if not order:
        # запасной поиск по Shp_tx
        tx = shp.get("Shp_tx") or ""
        if tx:
            order = social_db.get_donation_order_by_tx(tx)
    if not order:
        raise ValueError("Заказ не найден")

    expected = float(order.get("amount_rub") or 0)
    paid = float(out_sum.replace(",", "."))
    if abs(paid - expected) > 0.01:
        raise ValueError("Сумма не совпадает с заказом")

    tx_id = order["transaction_id"]
    if order.get("status") == "confirmed" and order.get("fulfilled"):
        return f"OK{inv_id}"

    social_db.update_donation_order(
        tx_id,
        status="confirmed",
        raw_callback=json.dumps(
            {"robokassa": True, "params": {k: str(v) for k, v in params.items()}},
            ensure_ascii=False,
        ),
    )
    # Всегда отвечаем OK после фиксации оплаты — иначе Robokassa может «потерять» callback.
    # Выдача привилегий догоняется здесь и через /status.
    try:
        order = social_db.get_donation_order_by_tx(tx_id)
        await fulfill_order_if_needed(order)
    except Exception:
        pass
    return f"OK{inv_id}"


async def mark_order_paid(transaction_id: str) -> dict:
    """Пользователь подтвердил, что перевёл деньги — ждём ручной проверки."""
    order = social_db.get_donation_order_by_tx(transaction_id)
    if not order:
        raise ValueError("Заказ не найден")
    status = order.get("status") or ""
    if status == "confirmed":
        return order
    if status in ("canceled", "failed", "chargebacked"):
        raise ValueError("Этот заказ уже закрыт")
    if status != "awaiting_confirmation":
        social_db.update_donation_order(transaction_id, status="awaiting_confirmation")
        order = social_db.get_donation_order_by_tx(transaction_id) or order
        _notify_admin_pending(order)
    return order


def _notify_admin_pending(order: dict) -> None:
    tx = order.get("transaction_id") or ""
    amount = order.get("amount_rub") or 0
    name = order.get("tier_name") or "заказ"
    contact = order.get("contact") or "—"
    discord_id = order.get("discord_id") or "—"
    player_id = order.get("player_id") or "—"
    product = order.get("product_type") or "tier"
    admin_url = f"{SITE_PUBLIC_URL}/#admin"
    subject = f"[Мини-станция] Оплата ожидает подтверждения · {amount} ₽"
    body = (
        f"Новая оплата СБП ожидает подтверждения.\n\n"
        f"Заказ: {tx}\n"
        f"Товар: {name} ({product})\n"
        f"Сумма: {amount} ₽\n"
        f"Контакт: {contact}\n"
        f"Discord ID: {discord_id}\n"
        f"Player ID: {player_id}\n\n"
        f"После проверки перевода в банке подтвердите заказ в админ-панели:\n"
        f"{admin_url}\n"
        f"Или API: POST /api/admin/donations/{tx}/confirm\n"
    )
    send_email(subject=subject, body=body, to=DONATION_NOTIFY_EMAIL)


async def fetch_payment_status(transaction_id: str) -> dict:
    if not platega_configured():
        raise ValueError("Платежи временно недоступны")
    url = f"{PLATEGA_API_BASE}/transaction/{transaction_id}"
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=_platega_headers()) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 400:
                raise ValueError((data or {}).get("message") or f"Ошибка статуса ({resp.status})")
            return data if isinstance(data, dict) else {"raw": data}


async def fulfill_order_if_needed(order: dict | None) -> dict | None:
    """Идемпотентно выдаёт спонсорство и/или монеты за confirmed заказ."""
    if not order:
        return order
    if order.get("status") != "confirmed":
        return order
    if order.get("fulfilled"):
        return order

    tx_id = order["transaction_id"]
    product_type = order.get("product_type") or "tier"
    coins = int(order.get("coins_amount") or 0)
    game_uuid = order.get("game_user_uuid") or ""
    if not game_uuid and order.get("payload"):
        try:
            meta = json.loads(order["payload"])
            game_uuid = meta.get("game_user_uuid") or ""
            coins = coins or int(meta.get("coins_amount") or 0)
        except Exception:
            pass

    if not social_db.mark_donation_fulfilled(tx_id):
        return social_db.get_donation_order_by_tx(tx_id)

    try:
        if product_type == "tier":
            discord_id = order.get("discord_id") or ""
            if not discord_id:
                # попытка из player_id вида discord_<id>
                pid = str(order.get("player_id") or "")
                if pid.startswith("discord_"):
                    discord_id = pid.replace("discord_", "", 1)
            if not discord_id:
                social_db.update_donation_order(tx_id, fulfilled=0)
                raise ValueError("Нет Discord ID — нельзя выдать спонсорство в игровой БД")
            tier_level = int(order.get("tier_id") or 0)
            if tier_level < 1 or tier_level > 5:
                social_db.update_donation_order(tx_id, fulfilled=0)
                raise ValueError("Некорректный уровень спонсорства")
            await upsert_discord_sponsor(discord_id, tier_level)
            if coins > 0 and game_uuid and not str(game_uuid).startswith("discord_"):
                await add_tokens(str(game_uuid), coins)
        elif product_type == "coins":
            if not game_uuid or str(game_uuid).startswith("discord_") or coins <= 0:
                social_db.update_donation_order(tx_id, fulfilled=0)
                return social_db.get_donation_order_by_tx(tx_id)
            await add_tokens(str(game_uuid), coins)
    except Exception:
        social_db.update_donation_order(tx_id, fulfilled=0)
        raise
    return social_db.get_donation_order_by_tx(tx_id)


async def confirm_order_manual(transaction_id: str, *, admin_name: str = "") -> dict:
    order = social_db.get_donation_order_by_tx(transaction_id)
    if not order:
        raise ValueError("Заказ не найден")
    if order.get("status") == "confirmed" and order.get("fulfilled"):
        return order
    social_db.update_donation_order(
        transaction_id,
        status="confirmed",
        raw_callback=json.dumps(
            {"manual_confirm": True, "by": admin_name or "admin"},
            ensure_ascii=False,
        ),
    )
    order = social_db.get_donation_order_by_tx(transaction_id)
    return await fulfill_order_if_needed(order) or order


async def apply_callback(payload: dict) -> dict:
    """Callback Platega: id + status (+ amount). Всегда фиксируем статус, выдачу — best effort."""
    tx_id = str(payload.get("id") or payload.get("transactionId") or "").strip()
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

    order = social_db.get_donation_order_by_tx(tx_id)
    if not order:
        raise ValueError("Заказ не найден")

    # проверка суммы, если пришла в callback
    amount = payload.get("amount")
    if amount is None and isinstance(payload.get("paymentDetails"), dict):
        amount = payload["paymentDetails"].get("amount")
    if amount is not None and status == "confirmed":
        try:
            paid = float(str(amount).replace(",", ".").replace(" ", "").replace("RUB", ""))
            expected = float(order.get("amount_rub") or 0)
            if abs(paid - expected) > 0.01:
                raise ValueError("Сумма callback не совпадает с заказом")
        except ValueError:
            raise
        except Exception:
            pass

    social_db.update_donation_order(
        tx_id,
        status=status,
        raw_callback=json.dumps(payload, ensure_ascii=False),
    )
    order = social_db.get_donation_order_by_tx(tx_id)
    if status == "confirmed":
        try:
            order = await fulfill_order_if_needed(order) or order
        except Exception:
            pass
    return {"ok": True, "transaction_id": tx_id, "status": status, "order": order}


def catalog_payload() -> dict:
    mode = payment_mode()
    active_raw = social_db.get_active_donation_discounts()
    active = [serialize_discount(d) for d in active_raw]
    promo = active_promo_summary()
    urls = {
        "callback": f"{SITE_PUBLIC_URL}/platega/callback",
        "callback_api": f"{SITE_PUBLIC_URL}/api/donations/platega/callback",
        "success": f"{SITE_PUBLIC_URL}/donate?paid=1",
        "fail": f"{SITE_PUBLIC_URL}/donate?paid=0",
    }
    if mode == "robokassa":
        urls.update({
            "result": f"{SITE_PUBLIC_URL}/api/donations/robokassa/result",
            "success": f"{SITE_PUBLIC_URL}/api/donations/robokassa/success",
            "fail": f"{SITE_PUBLIC_URL}/api/donations/robokassa/fail",
        })
    return {
        "configured": payments_available(),
        "mode": mode,
        "currency": "RUB",
        "tiers": list_tiers(active),
        "coin_packs": list_coin_packs(active),
        "methods": PAYMENT_METHODS,
        "default_method": int(PLATEGA_DEFAULT_METHOD or 2),
        "sbp": sbp_payment_info() if mode == "manual_sbp" else None,
        "smtp_ready": smtp_configured(),
        "urls": urls,
        "promo": promo,
        "discounts": active,
    }


def serialize_order(order: dict) -> dict:
    return {
        "transaction_id": order["transaction_id"],
        "status": order["status"],
        "product_type": order.get("product_type") or "tier",
        "tier_id": order.get("tier_id"),
        "tier_name": order.get("tier_name"),
        "coins_amount": order.get("coins_amount") or 0,
        "amount_rub": order["amount_rub"],
        "amount_label": _rub_label(int(order["amount_rub"] or 0)),
        "contact": order.get("contact"),
        "discord_id": order.get("discord_id"),
        "player_id": order.get("player_id"),
        "fulfilled": bool(order.get("fulfilled")),
        "created_at": order.get("created_at"),
        "sbp": None,
    }
