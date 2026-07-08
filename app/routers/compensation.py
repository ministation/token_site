from fastapi import APIRouter, Request, HTTPException

from app.dependencies import get_current_player, get_optional_user
from app.services.compensation import claim_compensation, get_public_compensation

router = APIRouter(prefix="/api/compensation", tags=["compensation"])


@router.get("/active")
async def compensation_active(request: Request):
    user = await get_optional_user(request)
    user_uuid = None
    if user and user.get("player"):
        user_uuid = user["player"]["user_uuid"]
    return get_public_compensation(user_uuid)


@router.post("/claim")
async def compensation_claim(request: Request):
    player = await get_current_player(request)
    result, err = await claim_compensation(player["user_uuid"])
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, **result}
