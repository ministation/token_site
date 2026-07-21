import json
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse

from app.config import PLATEGA_MERCHANT_ID, PLATEGA_SECRET
from app.dependencies import get_optional_social_user
from app.services import donations as donations_svc
import database_social as social_db

router = APIRouter(prefix="/api/donations", tags=["donations"])


@router.get("/catalog")
async def donation_catalog():
    return donations_svc.catalog_payload()


@router.get("/order/{transaction_id}")
async def donation_order(transaction_id: str):
    order = social_db.get_donation_order_by_tx(transaction_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return {
        "transaction_id": order["transaction_id"],
        "tier_id": order["tier_id"],
        "tier_name": order["tier_name"],
        "amount_rub": order["amount_rub"],
        "status": order["status"],
        "created_at": order["created_at"],
    }


@router.post("/checkout")
async def donation_checkout(
    request: Request,
    tier_id: int = Form(...),
    payment_method: int = Form(2),
    contact: str = Form(""),
):
    user = await get_optional_social_user(request)
    try:
        result = await donations_svc.create_payment(
            tier_id=tier_id,
            payment_method=payment_method,
            player_id=user["social_id"] if user else None,
            discord_id=user.get("discord_id") if user else None,
            contact=(contact or "").strip() or (user.get("username") if user else None),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Платёжный шлюз недоступен: {e}")
    return result


@router.get("/status/{transaction_id}")
async def donation_status(transaction_id: str):
    order = social_db.get_donation_order_by_tx(transaction_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    remote = None
    if donations_svc.platega_configured() and order.get("status") == "pending":
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
    return {
        "transaction_id": order["transaction_id"],
        "status": order["status"],
        "tier_name": order["tier_name"],
        "amount_rub": order["amount_rub"],
        "remote": remote,
    }


@router.post("/platega/callback")
async def platega_callback(request: Request):
    """Callback URL для ЛК Platega → Настройки → Callback URLs."""
    merchant = request.headers.get("X-MerchantId") or request.headers.get("x-merchantid")
    secret = request.headers.get("X-Secret") or request.headers.get("x-secret")
    if PLATEGA_MERCHANT_ID and merchant and merchant != PLATEGA_MERCHANT_ID:
        raise HTTPException(status_code=401, detail="Bad merchant")
    if PLATEGA_SECRET and secret and secret != PLATEGA_SECRET:
        raise HTTPException(status_code=401, detail="Bad secret")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    try:
        result = donations_svc.apply_callback(payload if isinstance(payload, dict) else {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse({"ok": True, **{k: result[k] for k in ("transaction_id", "status") if k in result}})
