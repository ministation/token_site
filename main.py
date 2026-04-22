from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncpg
import datetime
import random
import secrets
import aiohttp
import json
import os
import shutil
from pathlib import Path

# ✅ Загрузка переменных из .env
from dotenv import load_dotenv
load_dotenv()

# -------------------- КОНФИГУРАЦИЯ ИЗ .env --------------------
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
ADMIN_ROLE_IDS = [int(x.strip()) for x in os.getenv("ADMIN_ROLE_IDS", "").split(",") if x.strip()]
BANK_DEPOSIT_MIN = int(os.getenv("BANK_DEPOSIT_MIN", "10"))
BANK_DEPOSIT_RATE = int(os.getenv("BANK_DEPOSIT_RATE", "20"))
BANK_DEPOSIT_DAYS = int(os.getenv("BANK_DEPOSIT_DAYS", "7"))
BANK_LOAN_MAX = int(os.getenv("BANK_LOAN_MAX", "50"))
BANK_LOAN_RATE = int(os.getenv("BANK_LOAN_RATE", "30"))
BANK_LOAN_DAYS = int(os.getenv("BANK_LOAN_DAYS", "7"))
LOTTERY_COST = int(os.getenv("LOTTERY_COST", "5"))
MIN_TRANSFER = int(os.getenv("MIN_TRANSFER", "1"))
TRANSFER_COOLDOWN = int(os.getenv("TRANSFER_COOLDOWN", "60"))
MAX_CHAT_MESSAGES = int(os.getenv("MAX_CHAT_MESSAGES", "100"))
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8067"))
SESSIONS_FILE = os.getenv("SESSIONS_FILE", "sessions.json")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Импорт для соцсети
import database_social as social_db
from models_social import (
    SocialUserProfile, PostCreate, PostResponse, CommentCreate, CommentResponse,
    ProfileUpdate
)

# -------------------- ЗАГРУЗКА СЕССИЙ --------------------
def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_sessions(sessions):
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(sessions, f)

user_sessions = load_sessions()
transfer_cooldowns = {}
chat_messages = []

# -------------------- PYDANTIC МОДЕЛИ (для монеток) --------------------
class TransferRequest(BaseModel):
    receiver_nick: str
    amount: int

class DepositRequest(BaseModel):
    amount: int

class LoanRequest(BaseModel):
    amount: int

class WithdrawRequest(BaseModel):
    deposit_id: int

class RepayRequest(BaseModel):
    loan_id: int
    amount: Optional[int] = None

class AdminGiveRequest(BaseModel):
    target_nick: str
    amount: int

class ChatMessage(BaseModel):
    message: str

# -------------------- FASTAPI APP --------------------
app = FastAPI(title="SS14 Token Bank & Social")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db_pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(**DATABASE_CONFIG, min_size=1, max_size=10)
        print("✅ Подключено к PostgreSQL (игровая БД)")
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
    # SQLite уже инициализируется при импорте database_social
    print("✅ SQLite для соцсети готова")

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()

# -------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (монетки) --------------------
async def find_player_by_nick(nick: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT player_id, user_id::text as user_uuid, last_seen_user_name "
            "FROM player WHERE LOWER(last_seen_user_name) = LOWER($1) LIMIT 1",
            nick
        )
        if row:
            return {'player_id': row['player_id'], 'user_uuid': row['user_uuid'], 'last_seen_user_name': row['last_seen_user_name']}
        return None

async def find_player_by_discord(discord_id: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT p.player_id, p.user_id::text as user_uuid, p.last_seen_user_name 
            FROM player p JOIN discord_auth da ON p.user_id = da.user_id
            WHERE da.discord_id = $1::bigint LIMIT 1
        """, int(discord_id))
        if row:
            return {'player_id': row['player_id'], 'user_uuid': row['user_uuid'], 'last_seen_user_name': row['last_seen_user_name']}
        return None

async def get_balance(user_uuid: str) -> int:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(amount, 0) FROM player_antag_token "
            "WHERE player_id::text = $1 AND token_id = 'balance'",
            user_uuid
        )
        return row[0] if row else 0

async def add_tokens(user_uuid: str, amount: int):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT player_antag_token_id, amount FROM player_antag_token "
                "WHERE player_id::text = $1 AND token_id = 'balance'",
                user_uuid
            )
            if existing:
                new_amount = existing['amount'] + amount
                await conn.execute("UPDATE player_antag_token SET amount = $1 WHERE player_antag_token_id = $2", new_amount, existing['player_antag_token_id'])
                return new_amount
            else:
                await conn.execute("INSERT INTO player_antag_token (player_id, token_id, amount) VALUES ($1::uuid, 'balance', $2)", user_uuid, amount)
                return amount

async def remove_tokens(user_uuid: str, amount: int):
    async with db_pool.acquire() as conn:
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
                await conn.execute("DELETE FROM player_antag_token WHERE player_antag_token_id = $1", existing['player_antag_token_id'])
            else:
                await conn.execute("UPDATE player_antag_token SET amount = $1 WHERE player_antag_token_id = $2", new_amount, existing['player_antag_token_id'])
            return new_amount, None

async def transfer_tokens(sender_uuid: str, receiver_uuid: str, amount: int):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            balance = await get_balance(sender_uuid)
            if balance < amount:
                return None, None, "Недостаточно монет"
            new_sender, err = await remove_tokens(sender_uuid, amount)
            if err:
                return None, None, err
            new_receiver = await add_tokens(receiver_uuid, amount)
            return new_sender, new_receiver, None

async def get_top_players(limit: int = 30):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT pat.player_id::text as user_uuid, pat.amount AS balance, p.last_seen_user_name
            FROM player_antag_token pat
            JOIN player p ON pat.player_id::text = p.user_id::text
            WHERE pat.token_id = 'balance' AND pat.amount > 0
            ORDER BY balance DESC LIMIT $1
        """, limit)
        return [{'name': r['last_seen_user_name'], 'balance': r['balance']} for r in rows]

async def get_total_stats():
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT COUNT(DISTINCT player_id) as total_players, COALESCE(SUM(amount), 0) as total_tokens
            FROM player_antag_token WHERE token_id = 'balance' AND amount > 0
        """)
        return {'total_players': row['total_players'] if row else 0, 'total_tokens': row['total_tokens'] if row else 0}

async def get_bank_stats():
    async with db_pool.acquire() as conn:
        total_deposits = await conn.fetchval("SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='active'")
        total_loans = await conn.fetchval("SELECT COALESCE(SUM(remaining),0) FROM loans WHERE status='active'")
        return {'total_deposits': total_deposits or 0, 'total_loans': total_loans or 0, 'liquidity': (total_deposits or 0) - (total_loans or 0)}

async def get_active_deposits(user_uuid: str):
    async with db_pool.acquire() as conn:
        return await conn.fetch("SELECT deposit_id, amount, bonus, mature_at FROM deposits WHERE user_uuid = $1 AND status = 'active'", user_uuid)

async def get_active_loans(user_uuid: str):
    async with db_pool.acquire() as conn:
        return await conn.fetch("SELECT loan_id, amount, remaining, interest, due_at FROM loans WHERE user_uuid = $1 AND status = 'active'", user_uuid)

async def create_deposit(user_uuid: str, amount: int):
    mature_at = datetime.datetime.now() + datetime.timedelta(days=BANK_DEPOSIT_DAYS)
    bonus = amount * BANK_DEPOSIT_RATE // 100
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow("SELECT deposit_id FROM deposits WHERE user_uuid = $1 AND status = 'active'", user_uuid)
            if existing:
                return None, f"Уже есть активный депозит (ID: {existing['deposit_id']})"
            new_balance, err = await remove_tokens(user_uuid, amount)
            if err:
                return None, err
            await conn.execute("INSERT INTO deposits (user_uuid, amount, bonus, mature_at, status) VALUES ($1, $2, $3, $4, 'active')", user_uuid, amount, bonus, mature_at)
            deposit_id = await conn.fetchval("SELECT currval(pg_get_serial_sequence('deposits','deposit_id'))")
            return deposit_id, None

async def create_loan(user_uuid: str, amount: int):
    balance = await get_balance(user_uuid)
    max_loan = 20 if balance < 10 else 50 if balance >= 30 else 35
    if amount > max_loan:
        return None, f"Максимальная сумма займа: {max_loan} монет"
    bank = await get_bank_stats()
    if amount > bank['liquidity']:
        return None, f"Недостаточно средств в банке. Доступно: {bank['liquidity']} монет"
    due_at = datetime.datetime.now() + datetime.timedelta(days=BANK_LOAN_DAYS)
    interest = amount * BANK_LOAN_RATE // 100
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow("SELECT loan_id FROM loans WHERE user_uuid = $1 AND status = 'active'", user_uuid)
            if existing:
                return None, f"Уже есть активный заём (ID: {existing['loan_id']})"
            await conn.execute("INSERT INTO loans (user_uuid, amount, remaining, interest, due_at, status) VALUES ($1, $2, $3, $4, $5, 'active')", user_uuid, amount, amount + interest, interest, due_at)
            loan_id = await conn.fetchval("SELECT currval(pg_get_serial_sequence('loans','loan_id'))")
            await add_tokens(user_uuid, amount)
            return loan_id, None

async def withdraw_deposit(user_uuid: str, deposit_id: int):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            deposit = await conn.fetchrow("SELECT amount, bonus, mature_at FROM deposits WHERE deposit_id = $1 AND user_uuid = $2 AND status = 'active'", deposit_id, user_uuid)
            if not deposit:
                return False, "Вклад не найден"
            if deposit['mature_at'] > datetime.datetime.now():
                return False, f"Вклад созреет {deposit['mature_at'].strftime('%d.%m.%Y')}"
            total = deposit['amount'] + deposit['bonus']
            await add_tokens(user_uuid, total)
            await conn.execute("UPDATE deposits SET status = 'withdrawn' WHERE deposit_id = $1", deposit_id)
            return True, total

async def repay_loan(user_uuid: str, loan_id: int, amount: Optional[int] = None):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            loan = await conn.fetchrow("SELECT amount, remaining, interest FROM loans WHERE loan_id = $1 AND user_uuid = $2 AND status = 'active'", loan_id, user_uuid)
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
    if roll <= 60: return random.randint(1, 3)
    if roll <= 80: return random.randint(4, 8)
    if roll <= 92: return random.randint(9, 10)
    if roll <= 99: return random.randint(11, 15)
    return random.randint(16, 25)

# -------------------- АВТОРИЗАЦИЯ И ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ --------------------
def get_current_user(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token or session_token not in user_sessions:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user_sessions[session_token]

def get_current_player(request: Request):
    user = get_current_user(request)
    if 'player' not in user:
        raise HTTPException(status_code=403, detail="Discord не привязан к игровому аккаунту")
    return user['player']

async def ensure_social_user(player_data: dict, discord_data: dict):
    """Создает или обновляет запись в SQLite для соцсети"""
    return social_db.get_or_create_social_user(
        player_id=player_data['player_id'],
        user_uuid=player_data['user_uuid'],
        discord_id=discord_data['discord_id'],
        discord_username=discord_data['username'],
        discord_avatar=discord_data.get('avatar'),
        game_nickname=player_data['last_seen_user_name']
    )

# -------------------- DISCORD OAUTH2 --------------------
@app.get("/login")
async def login():
    state = secrets.token_urlsafe(16)
    user_sessions[state] = {"created": datetime.datetime.now().isoformat()}
    discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify&state={state}"
    return RedirectResponse(discord_auth_url)

@app.get("/callback")
async def callback(code: str, state: str):
    if state not in user_sessions:
        raise HTTPException(status_code=400, detail="Invalid state")
    async with aiohttp.ClientSession() as session:
        data = {'client_id': DISCORD_CLIENT_ID, 'client_secret': DISCORD_CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': DISCORD_REDIRECT_URI}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        async with session.post('https://discord.com/api/oauth2/token', data=data, headers=headers) as resp:
            token_data = await resp.json()
            access_token = token_data.get('access_token')
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bearer {access_token}'}
        async with session.get('https://discord.com/api/users/@me', headers=headers) as resp:
            user_data = await resp.json()
            discord_id = user_data['id']
            username = user_data['username']
            avatar = user_data.get('avatar')
    session_token = secrets.token_urlsafe(32)
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png" if avatar else None
    user_sessions[session_token] = {'discord_id': discord_id, 'username': username, 'avatar': avatar_url, 'created': datetime.datetime.now().isoformat()}
    player = await find_player_by_discord(discord_id)
    if player:
        user_sessions[session_token]['player'] = player
        # Создаем/обновляем профиль соцсети
        await ensure_social_user(player, user_sessions[session_token])
    response = RedirectResponse("/")
    response.set_cookie(key="session_token", value=session_token, httponly=True, max_age=30*24*3600)
    save_sessions(user_sessions)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse("/")
    response.delete_cookie("session_token")
    return response

@app.get("/api/me")
async def api_me(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token or session_token not in user_sessions:
        return {"authenticated": False}
    session = user_sessions[session_token]
    return {"authenticated": True, "username": session['username'], "discord_id": session['discord_id'], "avatar": session.get('avatar'), "player": session.get('player')}

# -------------------- РОУТЫ МОНЕТОК (существующие) --------------------
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/balance")
async def api_my_balance(request: Request):
    player = get_current_player(request)
    balance = await get_balance(player['user_uuid'])
    return {"nickname": player['last_seen_user_name'], "balance": balance}

@app.get("/api/balance/{nickname}")
async def api_balance(nickname: str):
    player = await find_player_by_nick(nickname)
    if not player:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    balance = await get_balance(player['user_uuid'])
    return {"nickname": player['last_seen_user_name'], "balance": balance}

@app.post("/api/transfer")
async def api_transfer(request: Request, req: TransferRequest):
    player = get_current_player(request)
    user_id = player['user_uuid']
    if user_id in transfer_cooldowns:
        elapsed = (datetime.datetime.now() - transfer_cooldowns[user_id]).total_seconds()
        if elapsed < TRANSFER_COOLDOWN:
            raise HTTPException(status_code=400, detail=f"Подождите {int(TRANSFER_COOLDOWN - elapsed)} сек")
    if req.amount < MIN_TRANSFER:
        raise HTTPException(status_code=400, detail=f"Минимальная сумма: {MIN_TRANSFER} монет")
    receiver = await find_player_by_nick(req.receiver_nick)
    if not receiver:
        raise HTTPException(status_code=404, detail="Получатель не найден")
    if player['user_uuid'] == receiver['user_uuid']:
        raise HTTPException(status_code=400, detail="Нельзя перевести самому себе")
    new_sender, new_receiver, err = await transfer_tokens(player['user_uuid'], receiver['user_uuid'], req.amount)
    if err:
        raise HTTPException(status_code=400, detail=err)
    transfer_cooldowns[user_id] = datetime.datetime.now()
    return {"success": True, "new_balance": new_sender, "amount": req.amount, "receiver": receiver['last_seen_user_name']}

@app.post("/api/lottery")
async def api_lottery(request: Request):
    player = get_current_player(request)
    balance = await get_balance(player['user_uuid'])
    if balance < LOTTERY_COST:
        raise HTTPException(status_code=400, detail=f"Недостаточно монет. Нужно {LOTTERY_COST}")
    new_balance, err = await remove_tokens(player['user_uuid'], LOTTERY_COST)
    if err:
        raise HTTPException(status_code=400, detail=err)
    prize = get_random_lottery_prize()
    final_balance = await add_tokens(player['user_uuid'], prize)
    return {"success": True, "prize": prize, "new_balance": final_balance}

@app.get("/api/deposits")
async def api_my_deposits(request: Request):
    player = get_current_player(request)
    deposits = await get_active_deposits(player['user_uuid'])
    return [{'deposit_id': d['deposit_id'], 'amount': d['amount'], 'bonus': d['bonus'], 'total': d['amount'] + d['bonus'], 'mature_at': d['mature_at'].isoformat(), 'mature_ts': int(d['mature_at'].timestamp())} for d in deposits]

@app.post("/api/deposit")
async def api_deposit(request: Request, req: DepositRequest):
    player = get_current_player(request)
    if req.amount < BANK_DEPOSIT_MIN:
        raise HTTPException(status_code=400, detail=f"Минимальная сумма: {BANK_DEPOSIT_MIN} монет")
    balance = await get_balance(player['user_uuid'])
    if balance < req.amount:
        raise HTTPException(status_code=400, detail=f"Недостаточно монет. У вас {balance}")
    deposit_id, err = await create_deposit(player['user_uuid'], req.amount)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "deposit_id": deposit_id}

@app.post("/api/withdraw")
async def api_withdraw(request: Request, req: WithdrawRequest):
    player = get_current_player(request)
    success, result = await withdraw_deposit(player['user_uuid'], req.deposit_id)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"success": True, "amount": result}

@app.get("/api/loans")
async def api_my_loans(request: Request):
    player = get_current_player(request)
    loans = await get_active_loans(player['user_uuid'])
    return [{'loan_id': l['loan_id'], 'amount': l['amount'], 'remaining': l['remaining'], 'interest': l['interest'], 'total': l['amount'] + l['interest'], 'due_at': l['due_at'].isoformat(), 'due_ts': int(l['due_at'].timestamp())} for l in loans]

@app.post("/api/loan")
async def api_loan(request: Request, req: LoanRequest):
    player = get_current_player(request)
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть положительной")
    loan_id, err = await create_loan(player['user_uuid'], req.amount)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "loan_id": loan_id}

@app.post("/api/repay")
async def api_repay(request: Request, req: RepayRequest):
    player = get_current_player(request)
    success, msg = await repay_loan(player['user_uuid'], req.loan_id, req.amount)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.get("/api/top")
async def api_top():
    players = await get_top_players(30)
    stats = await get_total_stats()
    bank = await get_bank_stats()
    return {"players": players, "stats": stats, "bank": bank}

@app.get("/api/stats")
async def api_stats():
    stats = await get_total_stats()
    bank = await get_bank_stats()
    return {"stats": stats, "bank": bank}

@app.get("/api/search")
async def api_search(q: str = ""):
    if not db_pool or len(q) < 2:
        return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT last_seen_user_name FROM player WHERE LOWER(last_seen_user_name) LIKE LOWER($1) LIMIT 10", f"%{q}%")
        return [r['last_seen_user_name'] for r in rows]

@app.post("/api/admin/give")
async def api_admin_give(request: Request, req: AdminGiveRequest):
    target = await find_player_by_nick(req.target_nick)
    if not target:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    new_balance = await add_tokens(target['user_uuid'], req.amount)
    return {"success": True, "new_balance": new_balance}

# -------------------- ЧАТ (простой) --------------------
@app.get("/api/chat")
async def get_chat():
    return chat_messages[-50:]

@app.post("/api/chat")
async def post_chat(request: Request, msg: ChatMessage):
    user = get_current_user(request)
    if len(msg.message) > 200:
        raise HTTPException(status_code=400, detail="Сообщение слишком длинное")
    if not msg.message.strip():
        raise HTTPException(status_code=400, detail="Пустое сообщение")
    
    chat_messages.append({
        "username": user['username'],
        "avatar": user.get('avatar'),
        "message": msg.message.strip(),
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    if len(chat_messages) > MAX_CHAT_MESSAGES:
        chat_messages.pop(0)
    
    return {"success": True}

# -------------------- СОЦСЕТЬ --------------------

# Профиль пользователя
@app.get("/profile/{player_id}")
async def profile_page(request: Request, player_id: str):
    # Проверяем существование профиля в соцсети
    profile = social_db.get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile})

@app.get("/api/social/profile/{player_id}")
async def api_get_profile(request: Request, player_id: str):
    current_user = get_current_user(request)
    my_player_id = current_user.get('player', {}).get('player_id')
    
    profile = social_db.get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    
    counts = social_db.get_follow_counts(player_id)
    is_following = False
    if my_player_id:
        is_following = social_db.is_following(my_player_id, player_id)
    
    return {
        "player_id": profile["player_id"],
        "game_nickname": profile["game_nickname"],
        "discord_username": profile["discord_username"],
        "discord_avatar": profile["discord_avatar"],
        "bio": profile["bio"],
        "following_count": counts["following"],
        "followers_count": counts["followers"],
        "is_following": is_following,
        "created_at": profile["created_at"]
    }

@app.post("/api/social/profile/update")
async def api_update_profile(request: Request, update: ProfileUpdate):
    player = get_current_player(request)
    social_db.update_social_user(player['player_id'], bio=update.bio)
    return {"success": True}

# Посты
@app.post("/api/social/posts")
async def api_create_post(
    request: Request,
    content: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    player = get_current_player(request)
    image_url = None
    if image:
        # Сохраняем изображение
        file_ext = os.path.splitext(image.filename)[1]
        filename = f"{player['player_id']}_{int(datetime.datetime.now().timestamp())}{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/{filename}"
    
    post_id = social_db.create_post(player['player_id'], content, image_url)
    return {"success": True, "post_id": post_id}

@app.get("/api/social/posts/feed")
async def api_feed(request: Request, limit: int = 20, offset: int = 0):
    player = get_current_player(request)
    posts = social_db.get_feed_posts(player['player_id'], limit, offset)
    # Преобразуем для ответа
    result = []
    for p in posts:
        result.append({
            "id": p["id"],
            "author_player_id": p["author_player_id"],
            "author_nickname": p["game_nickname"],
            "author_discord_username": p["discord_username"],
            "author_avatar": p["discord_avatar"],
            "content": p["content"],
            "image_url": p["image_url"],
            "like_count": p["like_count"],
            "comment_count": p["comment_count"],
            "liked_by_me": bool(p["liked_by_me"]),
            "created_at": p["created_at"]
        })
    return result

@app.get("/api/social/posts/user/{player_id}")
async def api_user_posts(request: Request, player_id: str, limit: int = 20, offset: int = 0):
    current_player = None
    try:
        current_player = get_current_player(request)
        viewer_id = current_player['player_id']
    except:
        viewer_id = None
    
    posts = social_db.get_user_posts(player_id, limit, offset)
    result = []
    for p in posts:
        liked = False
        if viewer_id:
            # Проверим лайк отдельно, т.к. в get_user_posts нет liked_by_me для viewer_id
            conn = social_db.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM likes WHERE post_id = ? AND player_id = ?", (p["id"], viewer_id))
            liked = cursor.fetchone() is not None
            conn.close()
        result.append({
            "id": p["id"],
            "author_player_id": p["author_player_id"],
            "author_nickname": p["game_nickname"],
            "author_discord_username": p["discord_username"],
            "author_avatar": p["discord_avatar"],
            "content": p["content"],
            "image_url": p["image_url"],
            "like_count": p["like_count"],
            "comment_count": p["comment_count"],
            "liked_by_me": liked,
            "created_at": p["created_at"]
        })
    return result

@app.delete("/api/social/posts/{post_id}")
async def api_delete_post(request: Request, post_id: int):
    player = get_current_player(request)
    success = social_db.delete_post(post_id, player['player_id'])
    if not success:
        raise HTTPException(status_code=404, detail="Пост не найден или нет прав")
    return {"success": True}

# Лайки
@app.post("/api/social/posts/{post_id}/like")
async def api_toggle_like(request: Request, post_id: int):
    player = get_current_player(request)
    action = social_db.toggle_like(post_id, player['player_id'])
    like_count = social_db.get_like_count(post_id)
    return {"action": action, "like_count": like_count}

# Комментарии
@app.post("/api/social/posts/{post_id}/comments")
async def api_add_comment(request: Request, post_id: int, comment: CommentCreate):
    player = get_current_player(request)
    comment_id = social_db.add_comment(post_id, player['player_id'], comment.content)
    return {"success": True, "comment_id": comment_id}

@app.get("/api/social/posts/{post_id}/comments")
async def api_get_comments(post_id: int):
    comments = social_db.get_comments(post_id)
    result = []
    for c in comments:
        result.append({
            "id": c["id"],
            "post_id": c["post_id"],
            "author_player_id": c["author_player_id"],
            "author_nickname": c["game_nickname"],
            "author_avatar": c["discord_avatar"],
            "content": c["content"],
            "created_at": c["created_at"]
        })
    return result

@app.delete("/api/social/comments/{comment_id}")
async def api_delete_comment(request: Request, comment_id: int):
    player = get_current_player(request)
    success = social_db.delete_comment(comment_id, player['player_id'])
    if not success:
        raise HTTPException(status_code=404, detail="Комментарий не найден или нет прав")
    return {"success": True}

# Подписки
@app.post("/api/social/follow/{target_player_id}")
async def api_follow(request: Request, target_player_id: str):
    player = get_current_player(request)
    if player['player_id'] == target_player_id:
        raise HTTPException(status_code=400, detail="Нельзя подписаться на себя")
    success = social_db.follow_user(player['player_id'], target_player_id)
    if not success:
        raise HTTPException(status_code=400, detail="Уже подписаны или ошибка")
    return {"success": True, "following": True}

@app.delete("/api/social/follow/{target_player_id}")
async def api_unfollow(request: Request, target_player_id: str):
    player = get_current_player(request)
    success = social_db.unfollow_user(player['player_id'], target_player_id)
    return {"success": success}

@app.get("/api/social/followers/{player_id}")
async def api_get_followers(player_id: str, limit: int = 20):
    followers = social_db.get_followers(player_id, limit)
    return followers

@app.get("/api/social/following/{player_id}")
async def api_get_following(player_id: str, limit: int = 20):
    following = social_db.get_following(player_id, limit)
    return following

# Поиск пользователей соцсети
@app.get("/api/social/search")
async def api_social_search(q: str, limit: int = 20):
    if len(q) < 2:
        return []
    results = social_db.search_social_users(q, limit)
    return results

# -------------------- ЗАПУСК --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)