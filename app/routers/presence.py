from fastapi import APIRouter, Request

from app.dependencies import get_current_social_user
from app.services import presence as presence_svc

router = APIRouter(prefix="/api/presence", tags=["presence"])


@router.post("/heartbeat")
async def presence_heartbeat(request: Request):
    user = await get_current_social_user(request)
    status = presence_svc.heartbeat(user["social_id"])
    return {"ok": True, "status": status}
