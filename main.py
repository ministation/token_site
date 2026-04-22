import os
import json
import secrets
import datetime
import random
import shutil
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, field_validator
import asyncpg
import aiohttp
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

# -------------------- КОНФИГУРАЦИЯ --------------------
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
ADMIN_DISCORD_IDS = set(x.strip() for x in os.getenv("ADMIN_DISCORD_IDS", "").split(",") if x.strip())
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
SOCIAL_DB_PATH = os.getenv("SOCIAL_DB_PATH", "social.db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------- НАСТРОЙКА БЕЗОПАСНОСТИ --------------------
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Мини-станция", docs_url=None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["85.192.49.3", "localhost", "127.0.0.1"])

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ --------------------
db_pool: asyncpg.Pool = None
user_sessions = {}
transfer_cooldowns = {}
chat_messages = []

# -------------------- ЗАГРУЗКА/СОХРАНЕНИЕ СЕССИЙ --------------------
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

# -------------------- PYDANTIC МОДЕЛИ (МОНЕТКИ) --------------------
class TransferRequest(BaseModel):
    receiver_nick: str
    amount: int
    @field_validator('amount')
    def positive(cls, v):
        if v <= 0: raise ValueError('Amount must be positive')
        return v

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

class ChatMessageRequest(BaseModel):
    message: str

# -------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (МОНЕТКИ) --------------------
async def find_player_by_nick(nick: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT player_id, user_id::text as user_uuid, last_seen_user_name FROM player WHERE LOWER(last_seen_user_name)=LOWER($1) LIMIT 1",
            nick
        )
        return {'player_id': row['player_id'], 'user_uuid': row['user_uuid'], 'last_seen_user_name': row['last_seen_user_name']} if row else None

async def find_player_by_discord(discord_id: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT p.player_id, p.user_id::text as user_uuid, p.last_seen_user_name 
            FROM player p JOIN discord_auth da ON p.user_id = da.user_id
            WHERE da.discord_id = $1::bigint LIMIT 1
        """, int(discord_id))
        return {'player_id': row['player_id'], 'user_uuid': row['user_uuid'], 'last_seen_user_name': row['last_seen_user_name']} if row else None

async def find_player_by_uuid(user_uuid: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT player_id, user_id::text as user_uuid, last_seen_user_name FROM player WHERE user_id::text = $1 LIMIT 1",
            user_uuid
        )
        return {'player_id': row['player_id'], 'user_uuid': row['user_uuid'], 'last_seen_user_name': row['last_seen_user_name']} if row else None

async def get_balance(user_uuid: str) -> int:
    async with db_pool.acquire() as conn:
        return await conn.fetchval("SELECT COALESCE(amount,0) FROM player_antag_token WHERE player_id::text=$1 AND token_id='balance'", user_uuid)

async def add_tokens(user_uuid: str, amount: int):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow("SELECT player_antag_token_id, amount FROM player_antag_token WHERE player_id::text=$1 AND token_id='balance'", user_uuid)
            if existing:
                new = existing['amount'] + amount
                await conn.execute("UPDATE player_antag_token SET amount=$1 WHERE player_antag_token_id=$2", new, existing['player_antag_token_id'])
                return new
            await conn.execute("INSERT INTO player_antag_token (player_id, token_id, amount) VALUES ($1::uuid, 'balance', $2)", user_uuid, amount)
            return amount

async def remove_tokens(user_uuid: str, amount: int):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow("SELECT player_antag_token_id, amount FROM player_antag_token WHERE player_id::text=$1 AND token_id='balance'", user_uuid)
            if not existing:
                return None, "Нет монет"
            if existing['amount'] < amount:
                return None, f"Только {existing['amount']} монет"
            new = existing['amount'] - amount
            if new == 0:
                await conn.execute("DELETE FROM player_antag_token WHERE player_antag_token_id=$1", existing['player_antag_token_id'])
            else:
                await conn.execute("UPDATE player_antag_token SET amount=$1 WHERE player_antag_token_id=$2", new, existing['player_antag_token_id'])
            return new, None

async def transfer_tokens(sender_uuid: str, receiver_uuid: str, amount: int):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            if await get_balance(sender_uuid) < amount:
                return None, None, "Недостаточно монет"
            new_sender, err = await remove_tokens(sender_uuid, amount)
            if err:
                return None, None, err
            new_receiver = await add_tokens(receiver_uuid, amount)
            return new_sender, new_receiver, None

async def get_top_players(limit: int = 30):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT pat.player_id::text as user_uuid, pat.amount, p.last_seen_user_name
            FROM player_antag_token pat JOIN player p ON pat.player_id::text = p.user_id::text
            WHERE pat.token_id='balance' AND pat.amount>0 ORDER BY pat.amount DESC LIMIT $1
        """, limit)
        return [{'name': r['last_seen_user_name'], 'balance': r['amount']} for r in rows]

async def get_total_stats():
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(DISTINCT player_id), COALESCE(SUM(amount),0) FROM player_antag_token WHERE token_id='balance' AND amount>0")
        return {'total_players': row[0] or 0, 'total_tokens': row[1] or 0}

async def get_bank_stats():
    async with db_pool.acquire() as conn:
        deposits = await conn.fetchval("SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='active'")
        loans = await conn.fetchval("SELECT COALESCE(SUM(remaining),0) FROM loans WHERE status='active'")
        return {'total_deposits': deposits or 0, 'total_loans': loans or 0, 'liquidity': (deposits or 0) - (loans or 0)}

async def get_active_deposits(user_uuid: str):
    async with db_pool.acquire() as conn:
        return await conn.fetch("SELECT deposit_id, amount, bonus, mature_at FROM deposits WHERE user_uuid=$1 AND status='active'", user_uuid)

async def get_active_loans(user_uuid: str):
    async with db_pool.acquire() as conn:
        return await conn.fetch("SELECT loan_id, amount, remaining, interest, due_at FROM loans WHERE user_uuid=$1 AND status='active'", user_uuid)

async def create_deposit(user_uuid: str, amount: int):
    mature_at = datetime.datetime.now() + datetime.timedelta(days=BANK_DEPOSIT_DAYS)
    bonus = amount * BANK_DEPOSIT_RATE // 100
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            if await conn.fetchval("SELECT 1 FROM deposits WHERE user_uuid=$1 AND status='active'", user_uuid):
                return None, "Уже есть активный депозит"
            new_balance, err = await remove_tokens(user_uuid, amount)
            if err:
                return None, err
            await conn.execute("INSERT INTO deposits (user_uuid, amount, bonus, mature_at, status) VALUES ($1,$2,$3,$4,'active')", user_uuid, amount, bonus, mature_at)
            return await conn.fetchval("SELECT currval('deposits_deposit_id_seq')"), None

async def create_loan(user_uuid: str, amount: int):
    balance = await get_balance(user_uuid)
    max_loan = 20 if balance < 10 else 50 if balance >= 30 else 35
    if amount > max_loan:
        return None, f"Максимум {max_loan} монет"
    bank = await get_bank_stats()
    if amount > bank['liquidity']:
        return None, f"В банке только {bank['liquidity']} монет"
    due_at = datetime.datetime.now() + datetime.timedelta(days=BANK_LOAN_DAYS)
    interest = amount * BANK_LOAN_RATE // 100
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            if await conn.fetchval("SELECT 1 FROM loans WHERE user_uuid=$1 AND status='active'", user_uuid):
                return None, "Уже есть активный заём"
            await conn.execute("INSERT INTO loans (user_uuid, amount, remaining, interest, due_at, status) VALUES ($1,$2,$3,$4,$5,'active')", user_uuid, amount, amount+interest, interest, due_at)
            loan_id = await conn.fetchval("SELECT currval('loans_loan_id_seq')")
            await add_tokens(user_uuid, amount)
            return loan_id, None

async def withdraw_deposit(user_uuid: str, deposit_id: int):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            deposit = await conn.fetchrow("SELECT amount, bonus, mature_at FROM deposits WHERE deposit_id=$1 AND user_uuid=$2 AND status='active'", deposit_id, user_uuid)
            if not deposit:
                return False, "Вклад не найден"
            if deposit['mature_at'] > datetime.datetime.now():
                return False, f"Созреет {deposit['mature_at'].strftime('%d.%m.%Y')}"
            total = deposit['amount'] + deposit['bonus']
            await add_tokens(user_uuid, total)
            await conn.execute("UPDATE deposits SET status='withdrawn' WHERE deposit_id=$1", deposit_id)
            return True, total

async def repay_loan(user_uuid: str, loan_id: int, amount: Optional[int] = None):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            loan = await conn.fetchrow("SELECT amount, remaining, interest FROM loans WHERE loan_id=$1 AND user_uuid=$2 AND status='active'", loan_id, user_uuid)
            if not loan:
                return False, "Заём не найден"
            total = loan['amount'] + loan['interest']
            repay = total if amount is None else amount
            if repay <= 0 or repay > total:
                return False, f"Сумма от 1 до {total}"
            if await get_balance(user_uuid) < repay:
                return False, "Недостаточно монет"
            await remove_tokens(user_uuid, repay)
            if repay >= total:
                await conn.execute("UPDATE loans SET status='repaid', remaining=0 WHERE loan_id=$1", loan_id)
                return True, f"Заём погашен. Возвращено {repay} монет"
            else:
                new_remaining = total - repay
                await conn.execute("UPDATE loans SET remaining=$1 WHERE loan_id=$2", new_remaining, loan_id)
                return True, f"Погашено {repay} монет. Остаток: {new_remaining}"

def get_random_lottery_prize():
    roll = random.randint(1, 100)
    if roll <= 75: return random.randint(1, 2)
    if roll <= 90: return random.randint(3, 4)
    if roll <= 97: return random.randint(5, 7)
    if roll <= 99: return random.randint(8, 12)
    return random.randint(15, 25)

# -------------------- АВТОРИЗАЦИЯ --------------------
def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in user_sessions:
        raise HTTPException(status_code=401)
    return user_sessions[token]

def get_current_player(request: Request):
    user = get_current_user(request)
    if 'player' not in user:
        raise HTTPException(status_code=403, detail="Привяжите игровой аккаунт")
    return user['player']

# -------------------- DISCORD OAUTH2 --------------------
@app.get("/login")
@limiter.limit("5/minute")
async def login(request: Request):
    state = secrets.token_urlsafe(16)
    user_sessions[state] = {"created": datetime.datetime.now().isoformat()}
    url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify&state={state}"
    return RedirectResponse(url)

# Вход по UUID (для игры) – привязка к сессии
@app.get("/login/{user_uuid}")
@limiter.limit("10/minute")
async def login_with_uuid(request: Request, user_uuid: str):
    player = await find_player_by_uuid(user_uuid)
    if not player:
        raise HTTPException(status_code=404, detail="Игрок с таким UUID не найден")
    token = request.cookies.get("session_token")
    if token and token in user_sessions:
        sess = user_sessions[token]
        sess['player'] = player
        import database_social as social_db
        social_db.get_or_create_social_user(player['player_id'], player['user_uuid'], sess.get('discord_id', ''), sess.get('username', ''), sess.get('avatar'), player['last_seen_user_name'])
        save_sessions(user_sessions)
        return RedirectResponse("/")
    session_token = secrets.token_urlsafe(32)
    user_sessions[session_token] = {
        'player': player,
        'created': datetime.datetime.now().isoformat()
    }
    response = RedirectResponse("/")
    response.set_cookie("session_token", session_token, httponly=True, max_age=30*24*3600)
    save_sessions(user_sessions)
    return response

@app.get("/callback")
@limiter.limit("10/minute")
async def callback(request: Request, code: str, state: str):
    if state not in user_sessions:
        raise HTTPException(status_code=400, detail="Invalid state")
    async with aiohttp.ClientSession() as sess:
        data = {'client_id': DISCORD_CLIENT_ID, 'client_secret': DISCORD_CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': DISCORD_REDIRECT_URI}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        async with sess.post('https://discord.com/api/oauth2/token', data=data, headers=headers) as resp:
            token_data = await resp.json()
            access_token = token_data.get('access_token')
    async with aiohttp.ClientSession() as sess:
        headers = {'Authorization': f'Bearer {access_token}'}
        async with sess.get('https://discord.com/api/users/@me', headers=headers) as resp:
            user_data = await resp.json()
            discord_id = user_data['id']
            username = user_data['username']
            avatar = user_data.get('avatar')
    session_token = secrets.token_urlsafe(32)
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png" if avatar else None
    user_sessions[session_token] = {
        'discord_id': discord_id,
        'username': username,
        'avatar': avatar_url,
        'is_admin': discord_id in ADMIN_DISCORD_IDS,
        'created': datetime.datetime.now().isoformat()
    }
    player = await find_player_by_discord(discord_id)
    if player:
        user_sessions[session_token]['player'] = player
        import database_social as social_db
        social_db.get_or_create_social_user(player['player_id'], player['user_uuid'], discord_id, username, avatar_url, player['last_seen_user_name'])
    response = RedirectResponse("/")
    response.set_cookie("session_token", session_token, httponly=True, max_age=30*24*3600)
    save_sessions(user_sessions)
    return response

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token and token in user_sessions:
        del user_sessions[token]
        save_sessions(user_sessions)
    response = RedirectResponse("/")
    response.delete_cookie("session_token")
    return response

@app.get("/api/me")
async def api_me(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in user_sessions:
        return {"authenticated": False}
    sess = user_sessions[token]
    return {
        "authenticated": True,
        "username": sess.get('username'),
        "avatar": sess.get('avatar'),
        "player": sess.get('player'),
        "is_admin": sess.get('is_admin', False)
    }

@app.post("/api/link_player")
@limiter.limit("5/minute")
async def link_player(request: Request):
    data = await request.json()
    user_uuid = data.get('user_uuid')
    if not user_uuid:
        raise HTTPException(400, "UUID required")
    player = await find_player_by_uuid(user_uuid)
    if not player:
        raise HTTPException(404, "Player not found")
    token = request.cookies.get("session_token")
    if not token or token not in user_sessions:
        raise HTTPException(401)
    user_sessions[token]['player'] = player
    sess = user_sessions[token]
    import database_social as social_db
    social_db.get_or_create_social_user(player['player_id'], player['user_uuid'], sess.get('discord_id', ''), sess.get('username', ''), sess.get('avatar'), player['last_seen_user_name'])
    save_sessions(user_sessions)
    return {"success": True}

# -------------------- МОНЕТКИ (API) --------------------
@app.get("/api/balance")
async def api_my_balance(request: Request):
    player = get_current_player(request)
    return {"nickname": player['last_seen_user_name'], "balance": await get_balance(player['user_uuid'])}

@app.get("/api/balance/{nickname}")
async def api_balance(nickname: str):
    player = await find_player_by_nick(nickname)
    if not player:
        raise HTTPException(404, "Игрок не найден")
    return {"nickname": player['last_seen_user_name'], "balance": await get_balance(player['user_uuid'])}

@app.post("/api/transfer")
@limiter.limit("5/minute")
async def api_transfer(request: Request, req: TransferRequest):
    player = get_current_player(request)
    if player['user_uuid'] in transfer_cooldowns:
        elapsed = (datetime.datetime.now() - transfer_cooldowns[player['user_uuid']]).total_seconds()
        if elapsed < TRANSFER_COOLDOWN:
            raise HTTPException(400, f"Подождите {int(TRANSFER_COOLDOWN-elapsed)}с")
    if req.amount < MIN_TRANSFER:
        raise HTTPException(400, f"Минимум {MIN_TRANSFER} монет")
    receiver = await find_player_by_nick(req.receiver_nick)
    if not receiver:
        raise HTTPException(404, "Получатель не найден")
    if player['user_uuid'] == receiver['user_uuid']:
        raise HTTPException(400, "Нельзя себе")
    new_sender, new_receiver, err = await transfer_tokens(player['user_uuid'], receiver['user_uuid'], req.amount)
    if err:
        raise HTTPException(400, err)
    transfer_cooldowns[player['user_uuid']] = datetime.datetime.now()
    return {"success": True, "new_balance": new_sender, "amount": req.amount, "receiver": receiver['last_seen_user_name']}

@app.post("/api/lottery")
@limiter.limit("10/minute")
async def api_lottery(request: Request):
    player = get_current_player(request)
    if await get_balance(player['user_uuid']) < LOTTERY_COST:
        raise HTTPException(400, f"Нужно {LOTTERY_COST} монет")
    new_balance, err = await remove_tokens(player['user_uuid'], LOTTERY_COST)
    if err:
        raise HTTPException(400, err)
    prize = get_random_lottery_prize()
    final_balance = await add_tokens(player['user_uuid'], prize)
    return {"success": True, "prize": prize, "new_balance": final_balance}

@app.get("/api/deposits")
async def api_my_deposits(request: Request):
    player = get_current_player(request)
    deposits = await get_active_deposits(player['user_uuid'])
    return [{'deposit_id': d['deposit_id'], 'amount': d['amount'], 'bonus': d['bonus'], 'total': d['amount']+d['bonus'], 'mature_at': d['mature_at'].isoformat(), 'mature_ts': int(d['mature_at'].timestamp())} for d in deposits]

@app.post("/api/deposit")
@limiter.limit("5/minute")
async def api_deposit(request: Request, req: DepositRequest):
    player = get_current_player(request)
    if req.amount < BANK_DEPOSIT_MIN:
        raise HTTPException(400, f"Минимум {BANK_DEPOSIT_MIN}")
    if await get_balance(player['user_uuid']) < req.amount:
        raise HTTPException(400, "Недостаточно монет")
    deposit_id, err = await create_deposit(player['user_uuid'], req.amount)
    if err:
        raise HTTPException(400, err)
    return {"success": True, "deposit_id": deposit_id}

@app.post("/api/withdraw")
async def api_withdraw(request: Request, req: WithdrawRequest):
    player = get_current_player(request)
    success, result = await withdraw_deposit(player['user_uuid'], req.deposit_id)
    if not success:
        raise HTTPException(400, result)
    return {"success": True, "amount": result}

@app.get("/api/loans")
async def api_my_loans(request: Request):
    player = get_current_player(request)
    loans = await get_active_loans(player['user_uuid'])
    return [{'loan_id': l['loan_id'], 'amount': l['amount'], 'remaining': l['remaining'], 'interest': l['interest'], 'total': l['amount']+l['interest'], 'due_at': l['due_at'].isoformat(), 'due_ts': int(l['due_at'].timestamp())} for l in loans]

@app.post("/api/loan")
@limiter.limit("3/day")
async def api_loan(request: Request, req: LoanRequest):
    player = get_current_player(request)
    if req.amount <= 0:
        raise HTTPException(400, "Сумма > 0")
    loan_id, err = await create_loan(player['user_uuid'], req.amount)
    if err:
        raise HTTPException(400, err)
    return {"success": True, "loan_id": loan_id}

@app.post("/api/repay")
async def api_repay(request: Request, req: RepayRequest):
    player = get_current_player(request)
    success, msg = await repay_loan(player['user_uuid'], req.loan_id, req.amount)
    if not success:
        raise HTTPException(400, msg)
    return {"success": True, "message": msg}

@app.get("/api/top")
async def api_top():
    return {"players": await get_top_players(30), "stats": await get_total_stats(), "bank": await get_bank_stats()}

@app.get("/api/stats")
async def api_stats():
    return {"stats": await get_total_stats(), "bank": await get_bank_stats()}

@app.get("/api/search")
async def api_search(q: str = ""):
    if len(q) < 2:
        return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT last_seen_user_name FROM player WHERE LOWER(last_seen_user_name) LIKE LOWER($1) LIMIT 10", f"%{q}%")
        return [r['last_seen_user_name'] for r in rows]

@app.post("/api/admin/give")
@limiter.limit("10/minute")
async def api_admin_give(request: Request, req: AdminGiveRequest):
    user = get_current_user(request)
    if not user.get('is_admin'):
        raise HTTPException(403)
    target = await find_player_by_nick(req.target_nick)
    if not target:
        raise HTTPException(404)
    new_balance = await add_tokens(target['user_uuid'], req.amount)
    return {"success": True, "new_balance": new_balance}

# -------------------- ЧАТ --------------------
@app.get("/api/chat")
async def get_chat():
    return chat_messages[-50:]

@app.post("/api/chat")
@limiter.limit("30/minute")
async def post_chat(request: Request, msg: ChatMessageRequest):
    user = get_current_user(request)
    chat_messages.append({"username": user.get('username', 'Гость'), "avatar": user.get('avatar'), "message": msg.message, "timestamp": datetime.datetime.now().isoformat()})
    if len(chat_messages) > MAX_CHAT_MESSAGES:
        chat_messages.pop(0)
    return {"success": True}

# -------------------- СОЦСЕТЬ --------------------
import database_social as social_db
from models_social import ProfileUpdate, PostCreate, CommentCreate, PrivateMessageRequest

@app.get("/")
@app.get("/profile/{player_id}")
@app.get("/messages")
async def index(request: Request, player_id: str = None):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/social/profile/{player_id}")
async def api_get_profile(request: Request, player_id: str):
    profile = social_db.get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(404)
    my_id = get_current_user(request).get('player', {}).get('player_id')
    counts = social_db.get_follow_counts(player_id)
    return {**profile, **counts, "is_following": social_db.is_following(my_id, player_id) if my_id else False}

@app.post("/api/social/profile/update")
@limiter.limit("10/minute")
async def api_update_profile(request: Request, update: ProfileUpdate):
    player = get_current_player(request)
    social_db.update_social_user(player['player_id'], bio=update.bio)
    return {"success": True}

@app.post("/api/social/posts")
@limiter.limit("20/minute")
async def api_create_post(request: Request, content: str = Form(...), image: Optional[UploadFile] = File(None)):
    player = get_current_player(request)
    image_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            raise HTTPException(400, "Неверный формат")
        filename = f"{player['player_id']}_{int(datetime.datetime.now().timestamp())}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/{filename}"
    post_id = social_db.create_post(player['player_id'], content, image_url)
    return {"success": True, "post_id": post_id}

@app.get("/api/social/posts/feed")
async def api_feed(request: Request, limit: int = 20, offset: int = 0):
    player = get_current_player(request)
    return social_db.get_feed_posts(player['player_id'], limit, offset)

@app.get("/api/social/posts/user/{player_id}")
async def api_user_posts(player_id: str, limit: int = 20, offset: int = 0):
    return social_db.get_user_posts(player_id, limit, offset)

@app.delete("/api/social/posts/{post_id}")
async def api_delete_post(request: Request, post_id: int):
    player = get_current_player(request)
    if not social_db.delete_post(post_id, player['player_id']):
        raise HTTPException(404)
    return {"success": True}

@app.post("/api/social/posts/{post_id}/like")
@limiter.limit("30/minute")
async def api_toggle_like(request: Request, post_id: int):
    player = get_current_player(request)
    action = social_db.toggle_like(post_id, player['player_id'])
    return {"action": action, "like_count": social_db.get_like_count(post_id)}

@app.post("/api/social/posts/{post_id}/comments")
@limiter.limit("20/minute")
async def api_add_comment(request: Request, post_id: int, comment: CommentCreate):
    player = get_current_player(request)
    comment_id = social_db.add_comment(post_id, player['player_id'], comment.content)
    return {"success": True, "comment_id": comment_id}

@app.get("/api/social/posts/{post_id}/comments")
async def api_get_comments(post_id: int):
    return social_db.get_comments(post_id)

@app.delete("/api/social/comments/{comment_id}")
async def api_delete_comment(request: Request, comment_id: int):
    player = get_current_player(request)
    if not social_db.delete_comment(comment_id, player['player_id']):
        raise HTTPException(404)
    return {"success": True}

@app.post("/api/social/follow/{target_player_id}")
@limiter.limit("20/minute")
async def api_follow(request: Request, target_player_id: str):
    player = get_current_player(request)
    if player['player_id'] == target_player_id:
        raise HTTPException(400)
    if not social_db.follow_user(player['player_id'], target_player_id):
        raise HTTPException(400)
    return {"success": True}

@app.delete("/api/social/follow/{target_player_id}")
async def api_unfollow(request: Request, target_player_id: str):
    player = get_current_player(request)
    social_db.unfollow_user(player['player_id'], target_player_id)
    return {"success": True}

@app.get("/api/social/followers/{player_id}")
async def api_get_followers(player_id: str):
    return social_db.get_followers(player_id)

@app.get("/api/social/following/{player_id}")
async def api_get_following(player_id: str):
    return social_db.get_following(player_id)

@app.get("/api/social/search")
async def api_social_search(q: str):
    if len(q) < 2:
        return []
    return social_db.search_social_users(q)

# -------------------- ЛИЧНЫЕ СООБЩЕНИЯ --------------------
@app.get("/api/notifications")
async def get_notifications(request: Request):
    user = get_current_user(request)
    player_id = user.get('player', {}).get('player_id')
    if not player_id:
        return {"unread_messages": 0, "unread_notifications": 0}
    unread = social_db.get_unread_messages_count(player_id)
    return {"unread_messages": unread, "unread_notifications": 0}

@app.get("/api/messages/conversations")
async def get_conversations(request: Request):
    player = get_current_player(request)
    return social_db.get_conversations(player['player_id'])

@app.get("/api/messages/{other_player_id}")
async def get_messages(request: Request, other_player_id: str):
    player = get_current_player(request)
    return social_db.get_private_messages(player['player_id'], other_player_id)

@app.post("/api/messages")
@limiter.limit("30/minute")
async def send_message(request: Request, req: PrivateMessageRequest):
    player = get_current_player(request)
    if player['player_id'] == req.receiver_player_id:
        raise HTTPException(400)
    social_db.send_private_message(player['player_id'], req.receiver_player_id, req.message)
    return {"success": True}

@app.post("/api/messages/{message_id}/read")
async def mark_message_read(request: Request, message_id: int):
    user = get_current_user(request)
    player_id = user.get('player', {}).get('player_id')
    if not player_id:
        raise HTTPException(403)
    social_db.mark_message_read(message_id, player_id)
    return {"success": True}

# -------------------- ЗАПУСК --------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(**DATABASE_CONFIG, min_size=1, max_size=10)
        print("✅ PostgreSQL ready")
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
    import database_social as social_db
    social_db.init_social_db(SOCIAL_DB_PATH)
    print("✅ SQLite ready")
    yield
    if db_pool:
        await db_pool.close()

app.router.lifespan_context = lifespan

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)