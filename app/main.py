from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import auth, bank, social, chat, pages  # <-- pages
from app.db.database import get_pg_pool, close_pg_pool
from app.core.sessions import load_sessions

app = FastAPI(title="SS14 Token Bank & Social")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup():
    load_sessions()
    await get_pg_pool()
    print("✅ Подключено к PostgreSQL (игровая БД)")
    print("✅ SQLite для соцсети готова")


@app.on_event("shutdown")
async def shutdown():
    await close_pg_pool()


# Главная страница
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Подключаем роутеры
app.include_router(auth.router)
app.include_router(bank.router)
app.include_router(social.router)
app.include_router(chat.router)
app.include_router(pages.router)   # роутер для HTML-страниц