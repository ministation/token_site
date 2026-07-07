from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException, Query

from app.dependencies import get_current_user
from app.services.playtime_transfer import get_job_playtimes, transfer_job_playtime
from app.services.bans import list_job_roles
from app.services.bank import find_player_by_nick

router = APIRouter(prefix="/api/playtime", tags=["playtime"])


class PlaytimeTransferRequest(BaseModel):
    player_nick: str = ""
    from_tracker: str
    to_tracker: str
    minutes: float = Field(gt=0)


def _can_manage_other_playtime(user: dict) -> bool:
    return bool(user.get("is_admin") or user.get("is_time_keeper"))


async def _resolve_target_uuid(user: dict, player_nick: str) -> tuple[str, str]:
    if player_nick.strip():
        if not _can_manage_other_playtime(user):
            raise HTTPException(status_code=403, detail="Перенос другим игрокам доступен хранителям времени")
        target = await find_player_by_nick(player_nick.strip())
        if not target:
            raise HTTPException(status_code=404, detail="Игрок не найден")
        return target["user_uuid"], target.get("last_seen_user_name") or player_nick.strip()
    if "player" not in user:
        raise HTTPException(status_code=403, detail="Discord не привязан к игровому аккаунту")
    player = user["player"]
    return player["user_uuid"], player.get("last_seen_user_name") or "Вы"


@router.get("/roles")
async def job_role_catalog(request: Request):
    await get_current_user(request)
    return list_job_roles()


@router.get("/jobs")
async def player_job_playtimes(request: Request, player_nick: str = Query("")):
    user = await get_current_user(request)
    user_uuid, name = await _resolve_target_uuid(user, player_nick)
    jobs = await get_job_playtimes(user_uuid)
    return {
        "player_name": name,
        "player_uuid": user_uuid,
        "jobs": jobs,
        "can_manage_others": _can_manage_other_playtime(user),
    }


@router.post("/transfer")
async def transfer_playtime(req: PlaytimeTransferRequest, request: Request):
    user = await get_current_user(request)
    user_uuid, name = await _resolve_target_uuid(user, req.player_nick)
    try:
        result = await transfer_job_playtime(user_uuid, req.from_tracker, req.to_tracker, req.minutes)
        result["player_name"] = name
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
