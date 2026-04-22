from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional
import asyncpg
import datetime
import secrets
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

# -------------------- КОНФИГУРАЦИЯ --------------------
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "144.31.0.187"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "ss14_db"),
    "user": os.getenv("DB_USER", "ss14_user"),
    "password": os.getenv("DB_PASSWORD", "18451845")
}

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1492275928875929763")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "2Ny_gvhxc40yiUQgNvGligD0P5UvIVvg")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://85.192.49.3:8067/callback")
SITE_TITLE = "Мини-станция"
SESSIONS_FILE = os.getenv("SESSIONS_FILE", "sessions.json")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------- ХРАНИЛИЩЕ СЕССИЙ --------------------
def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_sessions(sessions):
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(sessions, f)

user_sessions = load_sessions()

# -------------------- PYDANTIC МОДЕЛИ --------------------
class LinkPlayerRequest(BaseModel):
    user_uuid: str  # UUID игрока из SS14

# -------------------- FASTAPI --------------------
app = FastAPI(title=SITE_TITLE)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db_pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(**DATABASE_CONFIG, min_size=1, max_size=10)
        print("✅ PostgreSQL connected")
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()

# -------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ --------------------
async def find_player_by_uuid(user_uuid: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT player_id, user_id, last_seen_user_name FROM player WHERE user_id::text = $1 LIMIT 1",
            user_uuid
        )
        if row:
            return {
                "player_id": row["player_id"],
                "user_uuid": str(row["user_id"]),
                "last_seen_user_name": row["last_seen_user_name"]
            }
        return None

async def find_player_by_discord(discord_id: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT p.player_id, p.user_id::text as user_uuid, p.last_seen_user_name
            FROM player p
            JOIN discord_auth da ON p.user_id = da.user_id
            WHERE da.discord_id = $1::bigint
            LIMIT 1
        """, int(discord_id))
        if row:
            return {
                "player_id": row["player_id"],
                "user_uuid": row["user_uuid"],
                "last_seen_user_name": row["last_seen_user_name"]
            }
        return None

async def get_balance(user_uuid: str) -> int:
    async with db_pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COALESCE(amount, 0) FROM player_antag_token WHERE player_id::text = $1 AND token_id = 'balance'",
            user_uuid
        ) or 0

# -------------------- АВТОРИЗАЦИЯ --------------------
def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in user_sessions:
        raise HTTPException(401)
    return user_sessions[token]

@app.get("/login")
async def login():
    state = secrets.token_urlsafe(16)
    user_sessions[state] = {"created": datetime.datetime.now().isoformat()}
    url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify&state={state}"
    return RedirectResponse(url)

@app.get("/callback")
async def callback(code: str, state: str):
    if state not in user_sessions:
        raise HTTPException(400, "Invalid state")
    
    # Обмен кода на токен
    async with aiohttp.ClientSession() as sess:
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI
        }
        async with sess.post('https://discord.com/api/oauth2/token', data=data) as resp:
            token_data = await resp.json()
            access_token = token_data.get('access_token')
    
    # Получение пользователя Discord
    async with aiohttp.ClientSession() as sess:
        headers = {'Authorization': f'Bearer {access_token}'}
        async with sess.get('https://discord.com/api/users/@me', headers=headers) as resp:
            user_data = await resp.json()
            discord_id = user_data['id']
            username = user_data['username']
            avatar = user_data.get('avatar')
    
    session_token = secrets.token_urlsafe(32)
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png" if avatar else None
    
    # Проверяем, есть ли привязка к игровому аккаунту
    player = await find_player_by_discord(discord_id)
    
    user_sessions[session_token] = {
        "discord_id": discord_id,
        "username": username,
        "avatar": avatar_url,
        "player": player,
        "created": datetime.datetime.now().isoformat()
    }
    save_sessions(user_sessions)
    
    response = RedirectResponse("/")
    response.set_cookie("session_token", session_token, httponly=True, max_age=30*24*3600)
    return response

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token in user_sessions:
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
        "username": sess["username"],
        "avatar": sess.get("avatar"),
        "player": sess.get("player")
    }

# -------------------- ПРИВЯЗКА ИГРОВОГО АККАУНТА --------------------
@app.post("/api/link_player")
async def link_player(request: Request, req: LinkPlayerRequest):
    user = get_current_user(request)
    
    # Проверяем, существует ли игрок с таким UUID
    player = await find_player_by_uuid(req.user_uuid)
    if not player:
        raise HTTPException(404, "Игрок с таким UUID не найден")
    
    # Проверяем, не привязан ли уже этот аккаунт к другому Discord
    # (можно добавить логику)
    
    # Обновляем сессию
    user["player"] = player
    save_sessions(user_sessions)
    
    return {"success": True, "player": player}

# -------------------- ГЛАВНАЯ СТРАНИЦА --------------------
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": SITE_TITLE})

# -------------------- API ДЛЯ БАЛАНСА --------------------
@app.get("/api/balance")
async def get_my_balance(request: Request):
    user = get_current_user(request)
    if not user.get("player"):
        raise HTTPException(403, "Игровой аккаунт не привязан")
    balance = await get_balance(user["player"]["user_uuid"])
    return {"balance": balance, "nickname": user["player"]["last_seen_user_name"]}

# -------------------- ЗАПУСК --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8067)