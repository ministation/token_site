from fastapi import APIRouter, Request
from app.dependencies import get_current_social_user
from app.services.inventory import get_inventory

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
async def api_inventory(request: Request):
    user = await get_current_social_user(request)
    user_uuid = user.get("player", {}).get("user_uuid") if user.get("player") else user["social"].get("user_uuid")
    return await get_inventory(user["discord_id"], user_uuid)
