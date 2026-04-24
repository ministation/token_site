import datetime
import random
from typing import Optional
from app.db.database import get_pg_pool
from app.config import (
    BANK_DEPOSIT_MIN, BANK_DEPOSIT_RATE, BANK_DEPOSIT_DAYS,
    BANK_LOAN_MAX, BANK_LOAN_RATE, BANK_LOAN_DAYS,
    LOTTERY_COST, MIN_TRANSFER
)
from app.core.state import transfer_cooldowns
from fastapi import HTTPException


async def find_player_by_nick(nick: str):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT player_id, user_id::text as user_uuid, last_seen_user_name "
            "FROM player WHERE LOWER(last_seen_user_name) = LOWER($1) LIMIT 1",
            nick
        )
        if row:
            return {
                'player_id': row['player_id'],
                'user_uuid': row['user_uuid'],
                'last_seen_user_name': row['last_seen_user_name']
            }
        return None


async def find_player_by_discord(discord_id: str):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT p.player_id, p.user_id::text as user_uuid, p.last_seen_user_name
            FROM player p JOIN discord_auth da ON p.user_id = da.user_id
            WHERE da.discord_id = $1::bigint LIMIT 1
        """, int(discord_id))
        if row:
            return {
                'player_id': row['player_id'],
                'user_uuid': row['user_uuid'],
                'last_seen_user_name': row['last_seen_user_name']
            }
        return None


async def get_balance(user_uuid: str) -> int:
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(amount, 0) FROM player_antag_token "
            "WHERE player_id::text = $1 AND token_id = 'balance'",
            user_uuid
        )
        return row[0] if row else 0


async def add_tokens(user_uuid: str, amount: int) -> int:
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT player_antag_token_id, amount FROM player_antag_token "
                "WHERE player_id::text = $1 AND token_id = 'balance'",
                user_uuid
            )
            if existing:
                new_amount = existing['amount'] + amount
                await conn.execute(
                    "UPDATE player_antag_token SET amount = $1 WHERE player_antag_token_id = $2",
                    new_amount, existing['player_antag_token_id']
                )
                return new_amount
            else:
                await conn.execute(
                    "INSERT INTO player_antag_token (player_id, token_id, amount) VALUES ($1::uuid, 'balance', $2)",
                    user_uuid, amount
                )
                return amount


async def remove_tokens(user_uuid: str, amount: int) -> tuple[Optional[int], Optional[str]]:
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT player_antag_token_id, amount FROM player_antag_token "
                "WHERE player_id::text = $1 AND token_id = 'balance'",
                user_uuid
            )
            if not existing:
                return None, "Нет монет"
            if existing['amount'] < amount:
                return None, f"Только {existing['amount']} монет"
            new_amount = existing['amount'] - amount
            if new_amount == 0:
                await conn.execute(
                    "DELETE FROM player_antag_token WHERE player_antag_token_id = $1",
                    existing['player_antag_token_id']
                )
            else:
                await conn.execute(
                    "UPDATE player_antag_token SET amount = $1 WHERE player_antag_token_id = $2",
                    new_amount, existing['player_antag_token_id']
                )
            return new_amount, None


async def transfer_tokens(sender_uuid: str, receiver_uuid: str, amount: int):
    balance = await get_balance(sender_uuid)
    if balance < amount:
        return None, None, "Недостаточно монет"
    new_sender, err = await remove_tokens(sender_uuid, amount)
    if err:
        return None, None, err
    new_receiver = await add_tokens(receiver_uuid, amount)
    return new_sender, new_receiver, None


async def get_top_players(limit: int = 30):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT pat.player_id::text as user_uuid, pat.amount AS balance, p.last_seen_user_name
            FROM player_antag_token pat
            JOIN player p ON pat.player_id::text = p.user_id::text
            WHERE pat.token_id = 'balance' AND pat.amount > 0
            ORDER BY balance DESC LIMIT $1
        """, limit)
        return [{'name': r['last_seen_user_name'], 'balance': r['balance']} for r in rows]


async def get_total_stats():
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT COUNT(DISTINCT player_id) as total_players,
                   COALESCE(SUM(amount), 0) as total_tokens
            FROM player_antag_token WHERE token_id = 'balance' AND amount > 0
        """)
        return {
            'total_players': row['total_players'] if row else 0,
            'total_tokens': row['total_tokens'] if row else 0
        }


async def get_bank_stats():
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        total_deposits = await conn.fetchval("SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='active'")
        total_loans = await conn.fetchval("SELECT COALESCE(SUM(remaining),0) FROM loans WHERE status='active'")
        return {
            'total_deposits': total_deposits or 0,
            'total_loans': total_loans or 0,
            'liquidity': (total_deposits or 0) - (total_loans or 0)
        }


async def get_active_deposits(user_uuid: str):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        return await conn.fetch(
            "SELECT deposit_id, amount, bonus, mature_at FROM deposits WHERE user_uuid = $1 AND status = 'active'",
            user_uuid
        )


async def get_active_loans(user_uuid: str):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        return await conn.fetch(
            "SELECT loan_id, amount, remaining, interest, due_at FROM loans WHERE user_uuid = $1 AND status = 'active'",
            user_uuid
        )


async def create_deposit(user_uuid: str, amount: int):
    mature_at = datetime.datetime.now() + datetime.timedelta(days=BANK_DEPOSIT_DAYS)
    bonus = amount * BANK_DEPOSIT_RATE // 100
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT deposit_id FROM deposits WHERE user_uuid = $1 AND status = 'active'", user_uuid
            )
            if existing:
                return None, f"Уже есть активный депозит (ID: {existing['deposit_id']})"
            new_balance, err = await remove_tokens(user_uuid, amount)
            if err:
                return None, err
            await conn.execute(
                "INSERT INTO deposits (user_uuid, amount, bonus, mature_at, status) VALUES ($1, $2, $3, $4, 'active')",
                user_uuid, amount, bonus, mature_at
            )
            deposit_id = await conn.fetchval("SELECT currval(pg_get_serial_sequence('deposits','deposit_id'))")
            return deposit_id, None


async def create_loan(user_uuid: str, amount: int):
    balance = await get_balance(user_uuid)
    if balance < 10:
        max_loan = 20
    elif balance >= 30:
        max_loan = 50
    else:
        max_loan = 35
    if amount > max_loan:
        return None, f"Максимальная сумма займа: {max_loan} монет"
    bank = await get_bank_stats()
    if amount > bank['liquidity']:
        return None, f"Недостаточно средств в банке. Доступно: {bank['liquidity']} монет"
    due_at = datetime.datetime.now() + datetime.timedelta(days=BANK_LOAN_DAYS)
    interest = amount * BANK_LOAN_RATE // 100
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT loan_id FROM loans WHERE user_uuid = $1 AND status = 'active'", user_uuid
            )
            if existing:
                return None, f"Уже есть активный заём (ID: {existing['loan_id']})"
            await conn.execute(
                "INSERT INTO loans (user_uuid, amount, remaining, interest, due_at, status) VALUES ($1, $2, $3, $4, $5, 'active')",
                user_uuid, amount, amount + interest, interest, due_at
            )
            loan_id = await conn.fetchval("SELECT currval(pg_get_serial_sequence('loans','loan_id'))")
            await add_tokens(user_uuid, amount)
            return loan_id, None


async def withdraw_deposit(user_uuid: str, deposit_id: int):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            deposit = await conn.fetchrow(
                "SELECT amount, bonus, mature_at FROM deposits WHERE deposit_id = $1 AND user_uuid = $2 AND status = 'active'",
                deposit_id, user_uuid
            )
            if not deposit:
                return False, "Вклад не найден"
            if deposit['mature_at'] > datetime.datetime.now():
                return False, f"Вклад созреет {deposit['mature_at'].strftime('%d.%m.%Y')}"
            total = deposit['amount'] + deposit['bonus']
            await add_tokens(user_uuid, total)
            await conn.execute("UPDATE deposits SET status = 'withdrawn' WHERE deposit_id = $1", deposit_id)
            return True, total


async def repay_loan(user_uuid: str, loan_id: int, amount: Optional[int] = None):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            loan = await conn.fetchrow(
                "SELECT amount, remaining, interest FROM loans WHERE loan_id = $1 AND user_uuid = $2 AND status = 'active'",
                loan_id, user_uuid
            )
            if not loan:
                return False, "Заём не найден"
            total = loan['amount'] + loan['interest']
            repay = total if amount is None else amount
            if repay <= 0 or repay > total:
                return False, f"Сумма должна быть от 1 до {total}"
            balance = await get_balance(user_uuid)
            if balance < repay:
                return False, f"Недостаточно монет. Нужно {repay}, у вас {balance}"
            await remove_tokens(user_uuid, repay)
            if repay >= total:
                await conn.execute("UPDATE loans SET status = 'repaid', remaining = 0 WHERE loan_id = $1", loan_id)
                return True, f"Заём погашен. Возвращено {repay} монет"
            else:
                new_remaining = total - repay
                await conn.execute("UPDATE loans SET remaining = $1 WHERE loan_id = $2", new_remaining, loan_id)
                return True, f"Погашено {repay} монет. Остаток: {new_remaining}"


def get_random_lottery_prize():
    roll = random.randint(1, 100)
    if roll <= 60:
        return random.randint(1, 3)
    if roll <= 80:
        return random.randint(4, 8)
    if roll <= 92:
        return random.randint(9, 10)
    if roll <= 99:
        return random.randint(11, 15)
    return random.randint(16, 25)

async def search_all_players(query: str, limit: int = 20):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT p.last_seen_user_name, p.player_id::text as user_uuid,
                   COALESCE(pat.amount, 0) as balance
            FROM player p
            LEFT JOIN player_antag_token pat ON p.user_id = pat.player_id AND pat.token_id = 'balance'
            WHERE LOWER(p.last_seen_user_name) LIKE LOWER($1)
            ORDER BY balance DESC
            LIMIT $2
        """, f"%{query}%", limit)
        return [{"nickname": r["last_seen_user_name"],
                 "player_id": r["user_uuid"],
                 "balance": r["balance"]} for r in rows]
    
cat >> /home/ss14_user/token_site/app/services/bank.py << 'EOF'

async def get_balance_by_player_id(player_uuid: str) -> int:
    """Возвращает баланс игрока по его player_id (UUID)."""
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(amount, 0) FROM player_antag_token "
            "WHERE player_id::text = $1 AND token_id = 'balance'",
            player_uuid
        )
        return row[0] if row else 0
EOF