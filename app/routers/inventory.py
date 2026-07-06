from fastapi import APIRouter, Request
from app.dependencies import get_current_social_user
from app.services.inventory import get_inventory
from app.services.bank import find_player_by_discord

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
async def api_inventory(request: Request):
    user = await get_current_social_user(request)
    user_uuid = None

    if user.get("player"):
        user_uuid = user["player"].get("user_uuid")
    if not user_uuid or str(user_uuid).startswith("discord_"):
        linked = await find_player_by_discord(user["discord_id"])
        if linked:
            user_uuid = linked.get("user_uuid")
    if not user_uuid:
        social_uuid = user["social"].get("user_uuid")
        if social_uuid and not str(social_uuid).startswith("discord_"):
            user_uuid = social_uuid

    return await get_inventory(user["discord_id"], user_uuid)
