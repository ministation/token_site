from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.services.referral import apply_referral_code, get_referral_info
import database_social as social_db

router = APIRouter(prefix="/api/referral", tags=["referral"])


class ReferralApplyBody(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)


@router.get("/me")
async def referral_me(user: dict = Depends(get_current_user)):
    from app.services.auth_accounts import account_id_for_user
    account_id = account_id_for_user(user)
    if not account_id:
        return {}
    return get_referral_info(account_id)


@router.post("/apply")
async def referral_apply(body: ReferralApplyBody, user: dict = Depends(get_current_user)):
    from app.services.auth_accounts import account_id_for_user
    account_id = account_id_for_user(user)
    if not account_id:
        raise HTTPException(status_code=400, detail="Аккаунт не найден")
    ok, message = await apply_referral_code(account_id, body.code)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    social_db.complete_referral_prompt(account_id)
    return {"ok": True, "message": message, **get_referral_info(account_id)}


@router.post("/skip")
async def referral_skip(user: dict = Depends(get_current_user)):
    from app.services.auth_accounts import account_id_for_user
    account_id = account_id_for_user(user)
    if account_id:
        social_db.complete_referral_prompt(account_id)
    return {"ok": True, "needs_prompt": False}
