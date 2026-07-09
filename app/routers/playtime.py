from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException, Query

from app.dependencies import get_current_user
from app.services.playtime_transfer import (
    get_playtime_overview,
    transfer_job_playtime,
    bulk_add_job_playtime,
    build_unlock_all_plan,
    fetch_player_minutes_map,
)
from app.services.bans import list_job_roles, search_players
from app.services.bank import find_player_by_nick

router = APIRouter(prefix="/api/playtime", tags=["playtime"])


class PlaytimeTransferRequest(BaseModel):
    player_nick: str
    to_tracker: str
    minutes: float = Field(gt=0)
    from_tracker: str | None = None


class PlaytimeBulkItem(BaseModel):
    to_tracker: str
    minutes: float = Field(gt=0)


class PlaytimeBulkTransferRequest(BaseModel):
    player_nick: str
    transfers: list[PlaytimeBulkItem] = Field(min_length=1)
    from_tracker: str | None = None


class PlaytimeUnlockAllRequest(BaseModel):
    player_nick: str
    from_tracker: str | None = None


def _can_manage_playtime(user: dict) -> bool:
    return bool(user.get("is_admin") or user.get("is_time_keeper"))


def _require_manager(user: dict) -> None:
    if not _can_manage_playtime(user):
        raise HTTPException(
            status_code=403,
            detail="Накрутка времени доступна хранителям времени и администраторам",
        )


async def _resolve_target_uuid(player_nick: str) -> tuple[str, str]:
    nick = player_nick.strip()
    if not nick:
        raise HTTPException(status_code=400, detail="Укажите ник игрока")
    target = await find_player_by_nick(nick)
    if not target:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    return target["user_uuid"], target.get("last_seen_user_name") or nick


@router.get("/players/search")
async def playtime_player_search(request: Request, q: str = Query("", min_length=2)):
    user = await get_current_user(request)
    _require_manager(user)
    return await search_players(q, limit=15)


@router.get("/roles")
async def job_role_catalog(request: Request):
    user = await get_current_user(request)
    _require_manager(user)
    return list_job_roles()


@router.get("/overview")
async def player_playtime_overview(request: Request, player_nick: str = Query(..., min_length=1)):
    user = await get_current_user(request)
    _require_manager(user)
    user_uuid, name = await _resolve_target_uuid(player_nick)
    overview = await get_playtime_overview(user_uuid)
    return {
        "player_name": name,
        "player_uuid": user_uuid,
        **overview,
    }


@router.get("/jobs")
async def player_job_playtimes(request: Request, player_nick: str = Query(..., min_length=1)):
    return await player_playtime_overview(request, player_nick)


@router.post("/transfer")
async def transfer_playtime(req: PlaytimeTransferRequest, request: Request):
    user = await get_current_user(request)
    _require_manager(user)
    user_uuid, name = await _resolve_target_uuid(req.player_nick)
    try:
        result = await transfer_job_playtime(
            user_uuid, req.from_tracker or "", req.to_tracker, req.minutes,
        )
        result["player_name"] = name
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer/bulk")
async def transfer_playtime_bulk(req: PlaytimeBulkTransferRequest, request: Request):
    user = await get_current_user(request)
    _require_manager(user)
    user_uuid, name = await _resolve_target_uuid(req.player_nick)
    try:
        items = [(item.to_tracker, item.minutes) for item in req.transfers]
        result = await bulk_add_job_playtime(user_uuid, items)
        result["player_name"] = name
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/unlock-all")
async def unlock_all_roles(req: PlaytimeUnlockAllRequest, request: Request):
    user = await get_current_user(request)
    _require_manager(user)
    user_uuid, name = await _resolve_target_uuid(req.player_nick)
    try:
        minutes_map = await fetch_player_minutes_map(user_uuid)
        plan = build_unlock_all_plan(minutes_map, req.from_tracker)
        if not plan["transfers"]:
            return {
                "success": True,
                "player_name": name,
                "message": "Все роли уже разблокированы",
                "total_minutes": 0,
                "transfers": [],
            }
        items = [(t["to_tracker"], t["minutes"]) for t in plan["transfers"]]
        result = await bulk_add_job_playtime(user_uuid, items, enforce_limit=False)
        result["player_name"] = name
        result["message"] = f"Разблокировано ролей: {len(plan['transfers'])}"
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
