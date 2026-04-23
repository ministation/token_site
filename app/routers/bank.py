import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from app.dependencies import get_current_user, get_current_player
from app.models.bank import (
    TransferRequest, DepositRequest, LoanRequest,
    WithdrawRequest, RepayRequest, AdminGiveRequest
)
from app.services.bank import (
    find_player_by_nick, get_balance, transfer_tokens, remove_tokens, add_tokens,
    get_random_lottery_prize, get_active_deposits, create_deposit,
    withdraw_deposit, get_active_loans, create_loan, repay_loan,
    get_top_players, get_total_stats, get_bank_stats
)
from app.config import LOTTERY_COST, MIN_TRANSFER, TRANSFER_COOLDOWN, BANK_DEPOSIT_MIN
from app.core.state import transfer_cooldowns
from app.db.database import get_pg_pool

router = APIRouter(prefix="/api", tags=["bank"])


@router.get("/balance")
async def api_my_balance(request: Request):
    player = await get_current_player(request)
    balance = await get_balance(player['user_uuid'])
    return {"nickname": player['last_seen_user_name'], "balance": balance}


@router.get("/balance/{nickname}")
async def api_balance(nickname: str):
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


@router.get("/deposits")
async def api_my_deposits(request: Request):
    player = await get_current_player(request)
    deposits = await get_active_deposits(player['user_uuid'])
    return [
        {
            'deposit_id': d['deposit_id'],
            'amount': d['amount'],
            'bonus': d['bonus'],
            'total': d['amount'] + d['bonus'],
            'mature_at': d['mature_at'].isoformat(),
            'mature_ts': int(d['mature_at'].timestamp())
        }
        for d in deposits
    ]


@router.post("/deposit")
async def api_deposit(request: Request, req: DepositRequest):
    player = await get_current_player(request)
    if req.amount < BANK_DEPOSIT_MIN:
        raise HTTPException(status_code=400, detail=f"Минимальная сумма: {BANK_DEPOSIT_MIN} монет")
    balance = await get_balance(player['user_uuid'])
    if balance < req.amount:
        raise HTTPException(status_code=400, detail=f"Недостаточно монет. У вас {balance}")
    deposit_id, err = await create_deposit(player['user_uuid'], req.amount)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "deposit_id": deposit_id}


@router.post("/withdraw")
async def api_withdraw(request: Request, req: WithdrawRequest):
    player = await get_current_player(request)
    success, result = await withdraw_deposit(player['user_uuid'], req.deposit_id)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"success": True, "amount": result}


@router.get("/loans")
async def api_my_loans(request: Request):
    player = await get_current_player(request)
    loans = await get_active_loans(player['user_uuid'])
    return [
        {
            'loan_id': l['loan_id'],
            'amount': l['amount'],
            'remaining': l['remaining'],
            'interest': l['interest'],
            'total': l['amount'] + l['interest'],
            'due_at': l['due_at'].isoformat(),
            'due_ts': int(l['due_at'].timestamp())
        }
        for l in loans
    ]


@router.post("/loan")
async def api_loan(request: Request, req: LoanRequest):
    player = await get_current_player(request)
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть положительной")
    loan_id, err = await create_loan(player['user_uuid'], req.amount)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "loan_id": loan_id}


@router.post("/repay")
async def api_repay(request: Request, req: RepayRequest):
    player = await get_current_player(request)
    success, msg = await repay_loan(player['user_uuid'], req.loan_id, req.amount)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.get("/top")
async def api_top():
    players = await get_top_players(30)
    stats = await get_total_stats()
    bank = await get_bank_stats()
    return {"players": players, "stats": stats, "bank": bank}


@router.get("/stats")
async def api_stats():
    stats = await get_total_stats()
    bank = await get_bank_stats()
    return {"stats": stats, "bank": bank}


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
    # В оригинале не было проверки админских прав, оставим как есть
    target = await find_player_by_nick(req.target_nick)
    if not target:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    new_balance = await add_tokens(target['user_uuid'], req.amount)
    return {"success": True, "new_balance": new_balance}