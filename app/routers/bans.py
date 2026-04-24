from fastapi import APIRouter, Request, Query
from app.dependencies import get_current_player
from app.services.bans import get_all_bans, get_player_bans, get_playtime_stats

router = APIRouter(prefix="/api/bans", tags=["bans"])


@router.get("/all")
async def api_all_bans(limit: int = 50, offset: int = 0):
    return await get_all_bans(limit, offset)


@router.get("/my")
async def api_my_bans(request: Request):
    player = await get_current_player(request)
    return await get_player_bans(player["player_id"])


@router.get("/stats")
async def api_playtime_stats():
    return await get_playtime_stats()