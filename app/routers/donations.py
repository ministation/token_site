import html
import json
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

from app.config import PLATEGA_MERCHANT_ID, PLATEGA_SECRET
from app.dependencies import get_optional_social_user, get_current_admin
from app.services import donations as donations_svc
from app.services import robokassa
from app.core.ratelimit import enforce_cooldown, enforce_rate
import database_social as social_db

router = APIRouter(prefix="/api/donations", tags=["donations"])


@router.get("/catalog")
async def donation_catalog():
    return donations_svc.catalog_payload()


@router.get("/promo")
async def donation_promo():
    """Лёгкий endpoint для бейджа скидки на главной / в меню."""
    promo = donations_svc.active_promo_summary()
    return promo or {"has_sale": False}


@router.get("/order/{transaction_id}")
async def donation_order(transaction_id: str):
    order = social_db.get_donation_order_by_tx(transaction_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return donations_svc.serialize_order(order)


@router.post("/checkout")
async def donation_checkout(
    request: Request,
    product_type: str = Form("tier"),
    tier_id: int = Form(0),
    pack_id: int = Form(0),
    payment_method: int = Form(2),
    contact: str = Form(""),
):
    enforce_rate(request, "donate_checkout", limit=10, window=60.0, detail="Слишком много заказов.")
    user = await get_optional_social_user(request)
    game_uuid = donations_svc._resolve_game_uuid(user)
    try:
        result = await donations_svc.create_payment(
            product_type=product_type,
            tier_id=tier_id or None,
            pack_id=pack_id or None,
            payment_method=payment_method,
            player_id=user["social_id"] if user else None,
            discord_id=user.get("discord_id") if user else None,
            game_user_uuid=game_uuid,
            contact=(contact or "").strip() or (user.get("username") if user else None),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Не удалось создать заказ: {e}")
    return result


@router.post("/mark-paid/{transaction_id}")
async def donation_mark_paid(transaction_id: str, request: Request):
    enforce_rate(request, "donate_mark_paid", limit=12, window=60.0)
    enforce_cooldown(f"donate_paid:{transaction_id}", 5.0, detail="Уже отправлено, подождите.")
    try:
        order = await donations_svc.mark_order_paid(transaction_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "ok": True,
        **donations_svc.serialize_order(order),
        "message": "Платёж принят в обработку. Ожидайте зачисления.",
    }


@router.get("/status/{transaction_id}")
async def donation_status(transaction_id: str):
    order = social_db.get_donation_order_by_tx(transaction_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    remote = None
    mode = "manual_sbp"
    try:
        if order.get("payload"):
            mode = (json.loads(order["payload"]) or {}).get("mode") or mode
    except Exception:
        pass
    if (
        mode == "platega"
        and donations_svc.platega_configured()
        and order.get("status") == "pending"
    ):
        try:
            remote = await donations_svc.fetch_payment_status(transaction_id)
            st = str((remote or {}).get("status") or "").upper()
            if st == "CONFIRMED":
                social_db.update_donation_order(transaction_id, status="confirmed")
                order = social_db.get_donation_order_by_tx(transaction_id)
            elif st in ("CANCELED", "CANCELLED"):
                social_db.update_donation_order(transaction_id, status="canceled")
                order = social_db.get_donation_order_by_tx(transaction_id)
        except Exception:
            remote = None
    if order.get("status") == "confirmed":
        try:
            order = await donations_svc.fulfill_order_if_needed(order) or order
        except Exception:
            pass
    data = donations_svc.serialize_order(order)
    data["remote"] = remote
    return data


async def _robokassa_params(request: Request) -> dict:
    params: dict = {}
    params.update({k: v for k, v in request.query_params.items()})
    if request.method.upper() == "POST":
        ctype = (request.headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    params.update({k: str(v) for k, v in body.items()})
            except Exception:
                pass
        else:
            try:
                form = await request.form()
                for k in form.keys():
                    params[k] = str(form.get(k) or "")
            except Exception:
                pass
    return {k: ("" if v is None else str(v)) for k, v in params.items()}


@router.get("/robokassa/pay/{transaction_id}")
async def robokassa_pay_form(transaction_id: str):
    """Промежуточная страница: POST-форма на Robokassa (нужно для Receipt)."""
    order = social_db.get_donation_order_by_tx(transaction_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.get("status") in ("canceled", "failed"):
        raise HTTPException(status_code=400, detail="Заказ закрыт")
    try:
        meta = json.loads(order.get("payload") or "{}")
    except Exception:
        meta = {}
    fields = meta.get("robokassa_pay") or {}
    endpoint = meta.get("robokassa_endpoint") or robokassa.payment_endpoint()
    if not fields:
        if not robokassa.configured():
            raise HTTPException(status_code=503, detail="Robokassa не настроена")
        fields = robokassa.build_payment_params(
            amount_rub=int(order.get("amount_rub") or 0),
            inv_id=int(order["id"]),
            description=order.get("tier_name") or "Оплата",
            shp={"Shp_tx": transaction_id},
        )
        endpoint = robokassa.payment_endpoint()

    inputs = "\n".join(
        f'<input type="hidden" name="{html.escape(str(k))}" value="{html.escape(str(v))}">'
        for k, v in fields.items()
    )
    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Переход к оплате — Мини-станция</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background:#0f1410; color:#e8efe6;
           display:flex; min-height:100vh; align-items:center; justify-content:center; margin:0; }}
    .box {{ text-align:center; padding:24px; max-width:420px; }}
    .spin {{ width:28px; height:28px; border:3px solid #3a4a3c; border-top-color:#6fcf97;
             border-radius:50%; margin:0 auto 16px; animation:s .8s linear infinite; }}
    @keyframes s {{ to {{ transform:rotate(360deg); }} }}
    button {{ margin-top:16px; padding:12px 18px; border:0; border-radius:10px;
              background:#3d8b5f; color:#fff; font-weight:700; cursor:pointer; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="spin" aria-hidden="true"></div>
    <p>Переходим к оплате Robokassa…</p>
    <form id="rkPay" method="post" action="{html.escape(endpoint)}">
      {inputs}
      <noscript><button type="submit">Оплатить</button></noscript>
    </form>
  </div>
  <script>document.getElementById('rkPay').submit();</script>
</body>
</html>"""
    return HTMLResponse(page)


@router.api_route("/robokassa/result", methods=["GET", "POST"])
async def robokassa_result(request: Request):
    """Result URL для ЛК Robokassa. Ответ строго: OK{InvId}."""
    params = await _robokassa_params(request)
    try:
        body = await donations_svc.apply_robokassa_result(params)
        return PlainTextResponse(body, status_code=200)
    except ValueError as e:
        return PlainTextResponse(f"bad request: {e}", status_code=400)
    except Exception:
        return PlainTextResponse("error", status_code=500)


@router.api_route("/robokassa/success", methods=["GET", "POST"])
async def robokassa_success(request: Request):
    """Success URL — редирект пользователя на страницу доната."""
    params = await _robokassa_params(request)
    tx = (params.get("Shp_tx") or "").strip()
    inv = (params.get("InvId") or "").strip()
    if not tx and inv.isdigit():
        order = social_db.get_donation_order_by_id(int(inv))
        if order:
            tx = order["transaction_id"]
    if tx:
        return RedirectResponse(
            url=f"/donate?order={tx}&paid=1&result=success",
            status_code=302,
        )
    return RedirectResponse(url="/donate?paid=1", status_code=302)


@router.api_route("/robokassa/fail", methods=["GET", "POST"])
async def robokassa_fail(request: Request):
    params = await _robokassa_params(request)
    tx = (params.get("Shp_tx") or "").strip()
    inv = (params.get("InvId") or "").strip()
    if not tx and inv.isdigit():
        order = social_db.get_donation_order_by_id(int(inv))
        if order:
            tx = order["transaction_id"]
    if tx:
        return RedirectResponse(
            url=f"/donate?order={tx}&paid=0&result=fail",
            status_code=302,
        )
    return RedirectResponse(url="/donate?paid=0", status_code=302)


@router.post("/platega/callback")
async def platega_callback(request: Request):
    """Callback URL для ЛК Platega → Настройки → Callback URLs.
    Также доступен как POST /platega/callback (без /api/donations).
    """
    merchant = request.headers.get("X-MerchantId") or request.headers.get("x-merchantid")
    secret = request.headers.get("X-Secret") or request.headers.get("x-secret")
    if not PLATEGA_MERCHANT_ID or not PLATEGA_SECRET:
        raise HTTPException(status_code=503, detail="Platega не настроена")
    if merchant != PLATEGA_MERCHANT_ID or secret != PLATEGA_SECRET:
        raise HTTPException(status_code=401, detail="Bad credentials")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    try:
        result = await donations_svc.apply_callback(payload if isinstance(payload, dict) else {})
    except ValueError as e:
        # 200 не отдаём при явной ошибке данных — иначе Platega решит, что всё ок
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(
        {"ok": True, **{k: result[k] for k in ("transaction_id", "status") if k in result}},
        status_code=200,
    )


def _parse_ends_at(raw: str) -> str:
    """Принимает datetime-local / ISO, возвращает строку для SQLite."""
    s = (raw or "").strip().replace("T", " ")
    if not s:
        raise ValueError("Укажите дату окончания скидки")
    # datetime-local: 2026-07-22 23:59 or with seconds
    if len(s) == 16:
        s = s + ":00"
    return s


@router.get("/discounts")
async def list_discounts(request: Request, all: int = 0):
    """Публично — только активные; админ с all=1 — полный список."""
    user = await get_optional_social_user(request)
    is_admin = bool(user and user.get("is_admin"))
    if all and is_admin:
        rows = social_db.list_donation_discounts(include_inactive=True)
    else:
        rows = social_db.get_active_donation_discounts()
    return [donations_svc.serialize_discount(r) for r in rows]


@router.post("/discounts")
async def create_discount(
    request: Request,
    title: str = Form(...),
    percent: int = Form(...),
    scope: str = Form("all"),
    target_id: int = Form(0),
    badge_text: str = Form(""),
    starts_at: str = Form(""),
    ends_at: str = Form(...),
):
    admin = await get_current_admin(request)
    title = (title or "").strip()[:120]
    if not title:
        raise HTTPException(status_code=400, detail="Укажите название акции")
    percent = int(percent)
    if percent < 1 or percent > 90:
        raise HTTPException(status_code=400, detail="Скидка от 1% до 90%")
    scope = (scope or "all").strip().lower()
    allowed_scopes = {"all", "tiers", "coins", "tier", "pack"}
    if scope not in allowed_scopes:
        raise HTTPException(status_code=400, detail="Некорректная область скидки")
    tid = int(target_id or 0) or None
    if scope in ("tier", "pack") and not tid:
        raise HTTPException(status_code=400, detail="Выберите конкретный товар")
    if scope in ("all", "tiers", "coins"):
        tid = None
    try:
        ends = _parse_ends_at(ends_at)
        starts = _parse_ends_at(starts_at) if (starts_at or "").strip() else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    badge = (badge_text or "").strip()[:32] or None
    row = social_db.create_donation_discount(
        title=title,
        percent=percent,
        scope=scope,
        target_id=tid,
        badge_text=badge,
        starts_at=starts,
        ends_at=ends,
        created_by=str(admin.get("username") or admin.get("discord_id") or "admin"),
    )
    return {"ok": True, "discount": donations_svc.serialize_discount(row)}


@router.post("/discounts/{discount_id}/deactivate")
async def deactivate_discount(discount_id: int, request: Request):
    await get_current_admin(request)
    if not social_db.deactivate_donation_discount(discount_id):
        raise HTTPException(status_code=404, detail="Скидка не найдена")
    return {"ok": True}


@router.delete("/discounts/{discount_id}")
async def delete_discount(discount_id: int, request: Request):
    await get_current_admin(request)
    if not social_db.delete_donation_discount(discount_id):
        raise HTTPException(status_code=404, detail="Скидка не найдена")
    return {"ok": True}