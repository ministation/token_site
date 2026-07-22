import os
from dotenv import load_dotenv

load_dotenv()

# База данных PostgreSQL
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

# Discord OAuth2
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
ADMIN_ROLE_IDS = [int(x.strip()) for x in os.getenv("ADMIN_ROLE_IDS", "").split(",") if x.strip()]
ADMIN_USERNAMES = [
    x.strip().lower()
    for x in os.getenv("ADMIN_USERNAMES", "dotnet_build").split(",")
    if x.strip()
]
ADMIN_DISCORD_IDS = [
    x.strip()
    for x in os.getenv("ADMIN_DISCORD_IDS", "").split(",")
    if x.strip()
]
MODERATOR_USERNAMES = [
    x.strip().lower()
    for x in os.getenv("MODERATOR_USERNAMES", "").split(",")
    if x.strip()
]

# Discord-сервер и роли для автоматических тэгов
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")
CONTENT_MAKER_ROLE_IDS = [int(x.strip()) for x in os.getenv("CONTENT_MAKER_ROLE_IDS", "").split(",") if x.strip()]
TIME_KEEPER_ROLE_IDS = [int(x.strip()) for x in os.getenv("TIME_KEEPER_ROLE_IDS", "").split(",") if x.strip()]
CONTENT_MAKER_DISCORD_IDS = [x.strip() for x in os.getenv("CONTENT_MAKER_DISCORD_IDS", "").split(",") if x.strip()]
TIME_KEEPER_DISCORD_IDS = [x.strip() for x in os.getenv("TIME_KEEPER_DISCORD_IDS", "").split(",") if x.strip()]
CONTENT_MAKER_USERNAMES = [
    x.strip().lower()
    for x in os.getenv("CONTENT_MAKER_USERNAMES", "").split(",")
    if x.strip()
]
TIME_KEEPER_USERNAMES = [
    x.strip().lower()
    for x in os.getenv("TIME_KEEPER_USERNAMES", "").split(",")
    if x.strip()
]

# Банк (вклады и займы отключены)

# Лотерея и переводы
LOTTERY_COST = int(os.getenv("LOTTERY_COST", "5"))
MIN_TRANSFER = int(os.getenv("MIN_TRANSFER", "1"))
TRANSFER_COOLDOWN = int(os.getenv("TRANSFER_COOLDOWN", "60"))

# Чат
MAX_CHAT_MESSAGES = int(os.getenv("MAX_CHAT_MESSAGES", "100"))

SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "mini-station-14@yandex.ru")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+7 (965) 197-54-12")
SUPPORT_PHONE_TEL = os.getenv("SUPPORT_PHONE_TEL", "+79651975412")
SUPPORT_DISCORD_USERNAME = os.getenv("SUPPORT_DISCORD_USERNAME", "dotnet_build")
SUPPORT_TELEGRAM_USERNAME = os.getenv("SUPPORT_TELEGRAM_USERNAME", "mini_station_support")
BOOSTY_URL = os.getenv("BOOSTY_URL", "https://boosty.to/mini-station/")

# Реквизиты продавца (самозанятый) — для оферты / подвала сайта
SELLER_FULL_NAME = os.getenv("SELLER_FULL_NAME", "Омельченко Егор Романович")
SELLER_INN = os.getenv("SELLER_INN", "773475132921")
SELLER_STATUS = os.getenv("SELLER_STATUS", "Самозанятый")

SITE_PUBLIC_URL = os.getenv("SITE_PUBLIC_URL", "https://ministation.ru").rstrip("/")

# Platega.io — ключи выдаёт менеджер / ЛК «Настройки»
PLATEGA_MERCHANT_ID = os.getenv("PLATEGA_MERCHANT_ID", "")
PLATEGA_SECRET = os.getenv("PLATEGA_SECRET", "")
PLATEGA_API_BASE = os.getenv("PLATEGA_API_BASE", "https://app.platega.io").rstrip("/")
PLATEGA_DEFAULT_METHOD = int(os.getenv("PLATEGA_DEFAULT_METHOD", "2"))  # 2 = СБП/QR

# Файлы и загрузки
SESSIONS_FILE = os.getenv("SESSIONS_FILE", "sessions.json")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
AVATAR_DIR = os.getenv("AVATAR_DIR", "static/avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)

# Защита от абуза / нагрузки
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", str(1 * 1024 * 1024)))  # 1 MB
MAX_BODY_UPLOAD_BYTES = int(os.getenv("MAX_BODY_UPLOAD_BYTES", str(55 * 1024 * 1024)))  # 55 MB
ANTIBOT_SECRET = os.getenv("ANTIBOT_SECRET") or os.getenv("DISCORD_CLIENT_SECRET") or "change-me-antibot"
ANTIBOT_DIFFICULTY = int(os.getenv("ANTIBOT_DIFFICULTY", "3"))  # leading hex zeros in sha256

# Кулдауны записи (секунды)
COOLDOWN_CHAT_SEC = float(os.getenv("COOLDOWN_CHAT_SEC", "2"))
COOLDOWN_PM_SEC = float(os.getenv("COOLDOWN_PM_SEC", "2"))
COOLDOWN_COMMENT_SEC = float(os.getenv("COOLDOWN_COMMENT_SEC", "3"))
COOLDOWN_POST_SEC = float(os.getenv("COOLDOWN_POST_SEC", "30"))
COOLDOWN_TICKET_SEC = float(os.getenv("COOLDOWN_TICKET_SEC", "60"))
COOLDOWN_TICKET_MSG_SEC = float(os.getenv("COOLDOWN_TICKET_MSG_SEC", "5"))
COOLDOWN_LIKE_SEC = float(os.getenv("COOLDOWN_LIKE_SEC", "1"))
COOLDOWN_SEARCH_SEC = float(os.getenv("COOLDOWN_SEARCH_SEC", "0.4"))

# Ручная оплата СБП (QR / ссылка на перевод)
SBP_PAY_LINK = os.getenv(
    "SBP_PAY_LINK",
    "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79651975412&bankCode=100000000111",
)
SBP_QR_PATH = os.getenv("SBP_QR_PATH", "/static/payment/sbp-qr.png")
DONATION_NOTIFY_EMAIL = os.getenv("DONATION_NOTIFY_EMAIL", "proegorweb@gmail.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER or DONATION_NOTIFY_EMAIL
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1").strip().lower() not in ("0", "false", "no")
MANUAL_SBP_ENABLED = os.getenv("MANUAL_SBP_ENABLED", "1").strip().lower() not in ("0", "false", "no")
SPONSORSHIP_DAYS = int(os.getenv("SPONSORSHIP_DAYS", "30"))