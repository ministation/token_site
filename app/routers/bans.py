from fastapi import APIRouter, Request, HTTPException
from app.dependencies import get_current_user
from app.services.bans import get_player_bans
from app.services.bank import find_player_by_discord

router = APIRouter(prefix="/api/bans", tags=["bans"])


@router.get("/my")
async def api_my_bans(request: Request):
    user = await get_current_user(request)
    user_uuid = None
    ckey = None

    player = user.get("player")
    if player:
        user_uuid = player.get("user_uuid")
        ckey = player.get("last_seen_user_name")
    else:
        linked = await find_player_by_discord(user["discord_id"])
        if linked:
            user_uuid = linked.get("user_uuid")
            ckey = linked.get("last_seen_user_name")

    if not user_uuid and not ckey:
        raise HTTPException(
            status_code=403,
            detail="Привяжите Discord к игровому аккаунту, чтобы видеть наказания"
        )

    return await get_player_bans(user_uuid, ckey)
