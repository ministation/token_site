import asyncio
import hashlib
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from app.routers import auth, bank, social, chat, pages, messages, bans, online, stats, inventory, admin, playtime, compensation, presence, support, donations
from app.db.database import get_pg_pool, close_pg_pool
from app.core.sessions import load_sessions, get_session
from app.services.status_collector import collector_loop

import database_social as social_db

app = FastAPI(title="SS14 Token Bank & Social")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Единое окружение Jinja2 для всех шаблонов
env = Environment(loader=FileSystemLoader("templates"), auto_reload=True)
app.state.templates_env = env


def _visitor_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        ip = "unknown"
    ua = request.headers.get("user-agent", "")
    return hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:32]


def _should_track_visit(request: Request) -> bool:
    if request.method != "GET":
        return False
    path = request.url.path
    if path.startswith("/static") or path.startswith("/api"):
        return False
    return path == "/" or path.startswith("/profile/") or path == "/donate"


@app.middleware("http")
async def security_guards(request: Request, call_next):
    from app.core.ratelimit import body_limit_middleware, rate_limit_middleware

    async def after_body(req):
        return await rate_limit_middleware(req, call_next)

    return await body_limit_middleware(request, after_body)


@app.middleware("http")
async def track_page_visits(request: Request, call_next):
    response = await call_next(request)
    if response.status_code < 400 and _should_track_visit(request):
        try:
            discord_id = None
            token = request.cookies.get("session_token")
            if token:
                session = get_session(token)
                if session:
                    discord_id = session.get("discord_id")
            social_db.record_site_visit(request.url.path, _visitor_key(request), discord_id)
        except Exception:
            pass
    return response


@app.on_event("startup")
async def startup():
    load_sessions()
    social_db.cleanup_expired_sessions(30)
    from app.config import ADMIN_USERNAMES, MODERATOR_USERNAMES, CONTENT_MAKER_USERNAMES, TIME_KEEPER_USERNAMES
    for name in ADMIN_USERNAMES:
        social_db.seed_admin_by_username(name)
    for name in MODERATOR_USERNAMES:
        social_db.seed_moderator_by_username(name)
    for name in CONTENT_MAKER_USERNAMES:
        social_db.seed_content_maker_by_username(name)
    for name in TIME_KEEPER_USERNAMES:
        social_db.seed_time_keeper_by_username(name)
    await get_pg_pool()
    from app.services.bank import retire_deposits_and_loans
    closed = await retire_deposits_and_loans()
    if closed:
        print(f"✅ Закрыто активных вкладов: {closed}")
    from app.services.game_staff import sync_all_game_moderators_on_site
    from app.services.discord_badges import sync_all_member_badges
    synced = await sync_all_game_moderators_on_site()
    if synced:
        print(f"✅ Синхронизировано модераторов с игры: {synced}")
    badge_synced = await sync_all_member_badges()
    if badge_synced:
        print(f"✅ Синхронизированы тэги Discord: {badge_synced} аккаунтов")
    print("✅ Подключено к PostgreSQL (игровая БД)")
    print("✅ SQLite для соцсети готова")
    asyncio.create_task(collector_loop(interval=300))


@app.on_event("shutdown")
async def shutdown():
    await close_pg_pool()


@app.get("/")
async def index(request: Request):
    from app.seo import home_social_meta
    template = env.get_template("index.html")
    return HTMLResponse(template.render({"request": request, **home_social_meta(request)}))


app.include_router(auth.router)
app.include_router(bank.router)
app.include_router(social.router)
app.include_router(chat.router)
app.include_router(pages.router)
app.include_router(messages.router)
app.include_router(bans.router)
app.include_router(online.router)
app.include_router(presence.router)
app.include_router(support.router)
app.include_router(donations.router)
app.include_router(stats.router)
app.include_router(inventory.router)
app.include_router(admin.router)
app.include_router(playtime.router)
app.include_router(compensation.router)


@app.post("/platega/callback")
async def platega_callback_alias(request: Request):
    """Alias под URL из ЛК Platega: https://ministation.ru/platega/callback"""
    from app.routers.donations import platega_callback
    return await platega_callback(request)