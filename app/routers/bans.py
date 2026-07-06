from fastapi import Request
from app.dependencies import get_current_admin
from app.services.bans import get_all_bans, get_player_bans
from app.services.bank import find_player_by_discord
from fastapi import APIRouter, HTTPException
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/bans", tags=["bans"])


@router.get("/all")
async def api_all_bans(request: Request, limit: int = 50, offset: int = 0):
    """Все баны — только для администраторов (legacy-совместимость)."""
    await get_current_admin(request)
    return await get_all_bans(limit, offset)


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
