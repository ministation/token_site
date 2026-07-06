from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from app.dependencies import get_current_admin, get_current_social_user, get_current_user
from app.services.bans import get_all_bans, get_player_bans
from app.services.bank import find_player_by_discord
from app.services.appeals import submit_appeal, get_my_appeals, get_appeal_map
import database_social as social_db

router = APIRouter(prefix="/api/bans", tags=["bans"])


class BanAppealRequest(BaseModel):
    ban_id: int
    appeal_text: str


@router.get("/all")
async def api_all_bans(request: Request, limit: int = 50, offset: int = 0):
    await get_current_admin(request)
    return await get_all_bans(limit, offset)


@router.get("/my")
async def api_my_bans(request: Request):
    user = await get_current_user(request)
    user_uuid = None
    ckey = None
    social_id = None

    player = user.get("player")
    if player:
        user_uuid = player.get("user_uuid")
        ckey = player.get("last_seen_user_name")
    else:
        linked = await find_player_by_discord(user["discord_id"])
        if linked:
            user_uuid = linked.get("user_uuid")
            ckey = linked.get("last_seen_user_name")

    social = social_db.get_social_user_by_discord_id(user["discord_id"])
    if social:
        social_id = social["player_id"]

    if not user_uuid and not ckey:
        raise HTTPException(
            status_code=403,
            detail="Привяжите Discord к игровому аккаунту, чтобы видеть наказания"
        )

    bans = await get_player_bans(user_uuid, ckey)
    appeal_map = get_appeal_map(social_id) if social_id else {}
    for b in bans:
        appeal = appeal_map.get(b["ban_id"])
        if appeal:
            b["appeal"] = {
                "id": appeal["id"],
                "status": appeal["status"],
                "admin_response": appeal.get("admin_response"),
                "created_at": appeal["created_at"],
            }
        else:
            b["appeal"] = None
    return bans


@router.post("/appeal")
async def api_submit_appeal(req: BanAppealRequest, request: Request):
    user = await get_current_social_user(request)
    user_uuid = user.get("player", {}).get("user_uuid") if user.get("player") else None
    ckey = user.get("player", {}).get("last_seen_user_name") if user.get("player") else None
    if not user_uuid:
        linked = await find_player_by_discord(user["discord_id"])
        if linked:
            user_uuid = linked.get("user_uuid")
            ckey = linked.get("last_seen_user_name")
    try:
        appeal_id = submit_appeal(
            req.ban_id, user["social_id"], user_uuid, ckey, req.appeal_text
        )
        return {"success": True, "appeal_id": appeal_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/appeals/my")
async def api_my_appeals(request: Request):
    user = await get_current_social_user(request)
    return get_my_appeals(user["social_id"])
