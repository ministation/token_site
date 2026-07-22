import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from app.dependencies import get_current_user, get_current_player, get_current_admin
from app.models.bank import TransferRequest, AdminGiveRequest
from app.services.bank import (
    find_player_by_nick, get_balance, transfer_tokens, remove_tokens, add_tokens,
    get_random_lottery_prize,
    get_top_players, get_total_stats, search_all_players, get_playtime_stats
)
from app.config import LOTTERY_COST, MIN_TRANSFER, TRANSFER_COOLDOWN
from app.core.state import transfer_cooldowns
from app.db.database import get_pg_pool

router = APIRouter(prefix="/api", tags=["bank"])


@router.get("/balance")
async def api_my_balance(request: Request):
    player = await get_current_player(request)
    balance = await get_balance(player['user_uuid'])
    return {"nickname": player['last_seen_user_name'], "balance": balance}


@router.get("/balance/{nickname}")
async def api_balance(nickname: str, request: Request):
    await get_current_user(request)
    player = await find_player_by_nick(nickname)
    if not player:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    balance = await get_balance(player['user_uuid'])
    return {"nickname": player['last_seen_user_name'], "balance": balance}


@router.post("/transfer")
async def api_transfer(request: Request, req: TransferRequest):
    player = await get_current_player(request)
    user_uuid = player['user_uuid']

    # Проверка кулдауна
    if user_uuid in transfer_cooldowns:
        elapsed = (datetime.datetime.now() - transfer_cooldowns[user_uuid]).total_seconds()
        if elapsed < TRANSFER_COOLDOWN:
            raise HTTPException(
                status_code=400,
                detail=f"Подождите {int(TRANSFER_COOLDOWN - elapsed)} сек"
            )

    if req.amount < MIN_TRANSFER:
        raise HTTPException(status_code=400, detail=f"Минимальная сумма: {MIN_TRANSFER} монет")

    receiver = await find_player_by_nick(req.receiver_nick)
    if not receiver:
        raise HTTPException(status_code=404, detail="Получатель не найден")
    if player['user_uuid'] == receiver['user_uuid']:
        raise HTTPException(status_code=400, detail="Нельзя перевести самому себе")

    new_sender, new_receiver, err = await transfer_tokens(
        player['user_uuid'], receiver['user_uuid'], req.amount
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    transfer_cooldowns[user_uuid] = datetime.datetime.now()
    return {
        "success": True,
        "new_balance": new_sender,
        "amount": req.amount,
        "receiver": receiver['last_seen_user_name']
    }


@router.post("/lottery")
async def api_lottery(request: Request):
    player = await get_current_player(request)
    balance = await get_balance(player['user_uuid'])
    if balance < LOTTERY_COST:
        raise HTTPException(status_code=400, detail=f"Недостаточно монет. Нужно {LOTTERY_COST}")
    new_balance, err = await remove_tokens(player['user_uuid'], LOTTERY_COST)
    if err:
        raise HTTPException(status_code=400, detail=err)
    prize = get_random_lottery_prize()
    final_balance = await add_tokens(player['user_uuid'], prize)
    return {"success": True, "prize": prize, "new_balance": final_balance}


@router.get("/top")
async def api_top():
    players = await get_top_players(30)
    stats = await get_total_stats()
    return {"players": players, "stats": stats}


@router.get("/stats")
async def api_stats():
    stats = await get_total_stats()
    return {"stats": stats}


@router.get("/search")
async def api_search(q: str = Query("")):
    if not q or len(q) < 2:
        return []
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch(
            "SELECT last_seen_user_name FROM player WHERE LOWER(last_seen_user_name) LIKE LOWER($1) LIMIT 10",
            f"%{q}%"
        )
        return [r['last_seen_user_name'] for r in rows]


@router.post("/admin/give")
async def api_admin_give(request: Request, req: AdminGiveRequest):
    await get_current_admin(request)
    target = await find_player_by_nick(req.target_nick)
    if not target:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    new_balance = await add_tokens(target['user_uuid'], req.amount)
    return {"success": True, "new_balance": new_balance}

@router.get("/players/search")
async def api_players_search(request: Request, q: str = "", limit: int = 20):
    from app.core.ratelimit import enforce_rate
    if len(q) < 2:
        return []
    enforce_rate(request, "bank_search", limit=30, window=60.0, detail="Слишком частый поиск.")
    limit = min(max(limit, 1), 30)
    return await search_all_players(q, limit)


@router.get("/playtime-stats")
async def api_playtime_stats():
    return await get_playtime_stats()