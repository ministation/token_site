from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import auth, bank, social, chat
from app.db.database import get_pg_pool, close_pg_pool
from app.core.sessions import load_sessions
from app.core.state import transfer_cooldowns  # будет создан модуль для глобальных словарей

app = FastAPI(title="SS14 Token Bank & Social")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup():
    # Загружаем сессии
    load_sessions()
    # Инициализируем пул PostgreSQL
    await get_pg_pool()
    print("✅ Подключено к PostgreSQL (игровая БД)")
    print("✅ SQLite для соцсети готова (инициализируется при импорте)")


@app.on_event("shutdown")
async def shutdown():
    await close_pg_pool()


# Подключаем роутеры
app.include_router(auth.router)
app.include_router(bank.router)
app.include_router(social.router)
app.include_router(chat.router)