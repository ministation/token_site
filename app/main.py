import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from app.routers import auth, bank, social, chat, pages, messages, bans, online, stats, inventory, admin
from app.db.database import get_pg_pool, close_pg_pool
from app.core.sessions import load_sessions
from app.services.status_collector import collector_loop

import database_social as social_db

app = FastAPI(title="SS14 Token Bank & Social")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Единое окружение Jinja2 для всех шаблонов
env = Environment(loader=FileSystemLoader("templates"), auto_reload=True)
app.state.templates_env = env


@app.on_event("startup")
async def startup():
    load_sessions()
    social_db.cleanup_expired_sessions(30)
    from app.config import ADMIN_USERNAMES, MODERATOR_USERNAMES
    for name in ADMIN_USERNAMES:
        social_db.seed_admin_by_username(name)
    for name in MODERATOR_USERNAMES:
        social_db.seed_moderator_by_username(name)
    await get_pg_pool()
    print("✅ Подключено к PostgreSQL (игровая БД)")
    print("✅ SQLite для соцсети готова")
    asyncio.create_task(collector_loop(interval=300))


@app.on_event("shutdown")
async def shutdown():
    await close_pg_pool()


@app.get("/")
async def index(request: Request):
    template = env.get_template("index.html")
    return HTMLResponse(template.render({"request": request}))


app.include_router(auth.router)
app.include_router(bank.router)
app.include_router(social.router)
app.include_router(chat.router)
app.include_router(pages.router)
app.include_router(messages.router)
app.include_router(bans.router)
app.include_router(online.router)
app.include_router(stats.router)
app.include_router(inventory.router)
app.include_router(admin.router)