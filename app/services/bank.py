import random
from typing import Optional
from app.db.database import get_pg_pool


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


async def retire_deposits_and_loans():
    """Закрывает активные вклады и займы при отключении банковских механик."""
    pg = await get_pg_pool()
    closed_deposits = 0
    async with pg.acquire() as conn:
        deposits = await conn.fetch(
            "SELECT deposit_id, user_uuid, amount FROM deposits WHERE status = 'active'"
        )
        for d in deposits:
            async with conn.transaction():
                existing = await conn.fetchrow(
                    "SELECT player_antag_token_id, amount FROM player_antag_token "
                    "WHERE player_id::text = $1 AND token_id = 'balance'",
                    d['user_uuid'],
                )
                if existing:
                    await conn.execute(
                        "UPDATE player_antag_token SET amount = $1 WHERE player_antag_token_id = $2",
                        existing['amount'] + d['amount'], existing['player_antag_token_id'],
                    )
                else:
                    await conn.execute(
                        "INSERT INTO player_antag_token (player_id, token_id, amount) VALUES ($1::uuid, 'balance', $2)",
                        d['user_uuid'], d['amount'],
                    )
                await conn.execute(
                    "UPDATE deposits SET status = 'cancelled' WHERE deposit_id = $1",
                    d['deposit_id'],
                )
                closed_deposits += 1
        await conn.execute(
            "UPDATE loans SET status = 'cancelled', remaining = 0 WHERE status = 'active'"
        )
    return closed_deposits


def get_random_lottery_prize():
    roll = random.randint(1, 100)
    if roll <= 70:
        return random.randint(1, 3)
    if roll <= 88:
        return random.randint(4, 6)
    if roll <= 96:
        return random.randint(7, 9)
    if roll <= 99:
        return random.randint(10, 12)
    return random.randint(13, 18)

async def search_all_players(query: str, limit: int = 50):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        if query == "%%":
            # Все игроки
            rows = await conn.fetch("""
                SELECT p.last_seen_user_name, p.player_id, 
                       COALESCE(pat.amount, 0) as balance
                FROM player p
                LEFT JOIN player_antag_token pat ON p.user_id = pat.player_id AND pat.token_id = 'balance'
                ORDER BY balance DESC
                LIMIT $1
            """, limit)
        else:
            rows = await conn.fetch("""
                SELECT p.last_seen_user_name, p.player_id, 
                       COALESCE(pat.amount, 0) as balance
                FROM player p
                LEFT JOIN player_antag_token pat ON p.user_id = pat.player_id AND pat.token_id = 'balance'
                WHERE LOWER(p.last_seen_user_name) LIKE LOWER($1)
                ORDER BY balance DESC
                LIMIT $2
            """, query, limit)
        return [{"nickname": r["last_seen_user_name"],
                 "player_id": str(r["player_id"]),
                 "balance": r["balance"]} for r in rows]
    
async def get_balance_by_player_id(player_uuid: str) -> int:
    """Возвращает баланс игрока по game player_id (UUID)."""
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT COALESCE(pat.amount, 0) as balance
            FROM player p
            LEFT JOIN player_antag_token pat
                ON p.user_id = pat.player_id AND pat.token_id = 'balance'
            WHERE p.player_id::text = $1
        """, player_uuid)
        return int(row["balance"]) if row else 0


async def get_playtime_stats():
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow("""
            WITH player_totals AS (
                SELECT player_id, SUM(time_spent) AS total_time
                FROM play_time
                WHERE tracker = 'Overall'
                GROUP BY player_id
                HAVING SUM(time_spent) > interval '5 hours'
            )
            SELECT
                COUNT(*) FILTER (WHERE total_time < interval '50 hours') AS newbies,
                COUNT(*) FILTER (WHERE total_time >= interval '50 hours'
                                 AND total_time <= interval '400 hours') AS regulars,
                COUNT(*) FILTER (WHERE total_time > interval '400 hours') AS veterans,
                COUNT(*) AS total
            FROM player_totals
        """)
        return {
            "newbies": row["newbies"] or 0,
            "regulars": row["regulars"] or 0,
            "veterans": row["veterans"] or 0,
            "total": row["total"] or 0,
        }