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
# Выдача роли «Авторизован» после входа на сайт (Mini + Oasis)
# DISCORD_AUTH_ROLES=guild:role,guild:role  или раздельные переменные ниже
DISCORD_AUTH_ROLES = os.getenv("DISCORD_AUTH_ROLES", "").strip()
DISCORD_AUTH_ROLE_ID = os.getenv("DISCORD_AUTH_ROLE_ID", "").strip()
DISCORD_GUILD2_ID = os.getenv("DISCORD_GUILD2_ID", "").strip()
DISCORD_AUTH_ROLE_ID_2 = os.getenv("DISCORD_AUTH_ROLE_ID_2", "").strip()
DISCORD_GUILD2_BOT_TOKEN = os.getenv("DISCORD_GUILD2_BOT_TOKEN", "").strip()
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

# Discord-роли спонсоров: level:role_id (как в token_bot)
# После оплаты подписки сайт выдаёт роль, монеты за подписку не начисляет.
def _parse_level_role_map(raw: str) -> dict[int, int]:
    out: dict[int, int] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        level_s, role_s = part.split(":", 1)
        try:
            out[int(level_s.strip())] = int(role_s.strip())
        except ValueError:
            continue
    return out


SPONSOR_ROLE_IDS = _parse_level_role_map(
    os.getenv(
        "SPONSOR_ROLE_IDS",
        "1:1350474782482628700,2:1352353230964916274,3:1352359474685415505,"
        "4:1452826150954074253,5:1358872737673646130",
    )
)

# Банк (вклады и займы отключены)

# Лотерея и переводы
LOTTERY_COST = int(os.getenv("LOTTERY_COST", "5"))
MIN_TRANSFER = int(os.getenv("MIN_TRANSFER", "1"))
TRANSFER_COOLDOWN = int(os.getenv("TRANSFER_COOLDOWN", "60"))

# Чат
MAX_CHAT_MESSAGES = int(os.getenv("MAX_CHAT_MESSAGES", "100"))

SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "mini-station-14@yandex.ru")
SUPPORT_DISCORD_USERNAME = os.getenv("SUPPORT_DISCORD_USERNAME", "dotnet_build")
SUPPORT_TELEGRAM_USERNAME = os.getenv("SUPPORT_TELEGRAM_USERNAME", "mini_station_support")
BOOSTY_URL = os.getenv("BOOSTY_URL", "https://boosty.to/mini-station/")

# Реквизиты продавца (самозанятый) — для оферты / подвала сайта
SELLER_FULL_NAME = os.getenv("SELLER_FULL_NAME", "Омельченко Егор Романович")
SELLER_INN = os.getenv("SELLER_INN", "773475132921")
SELLER_STATUS = os.getenv("SELLER_STATUS", "Самозанятый")

SITE_PUBLIC_URL = os.getenv("SITE_PUBLIC_URL", "https://ministation.ru").rstrip("/")

# Shared secret with discord_auth_ss14 for auto-login after in-game Discord linking
GAME_AUTH_SECRET = os.getenv("GAME_AUTH_SECRET", "").strip()

# SS14: статус онлайна и адрес прямого подключения (лаунчер)
GAME_STATUS_URL = os.getenv("GAME_STATUS_URL", "http://ss14.ministation.ru:1214/status").rstrip("/")
GAME_CONNECT_ADDRESS = os.getenv("GAME_CONNECT_ADDRESS", "ss14://ss14.ministation.ru:1214")

# Platega.io — ключи выдаёт менеджер / ЛК «Настройки»
# По умолчанию выключена (сомнительный провайдер); код/callback остаются на случай включения.
PLATEGA_ENABLED = os.getenv("PLATEGA_ENABLED", "0").strip().lower() in ("1", "true", "yes")
PLATEGA_MERCHANT_ID = os.getenv("PLATEGA_MERCHANT_ID", "")
PLATEGA_SECRET = os.getenv("PLATEGA_SECRET", "")
PLATEGA_API_BASE = os.getenv("PLATEGA_API_BASE", "https://app.platega.io").rstrip("/")
PLATEGA_DEFAULT_METHOD = int(os.getenv("PLATEGA_DEFAULT_METHOD", "2"))  # 2 = СБП/QR, 11 = карты МИР/RUB

# Robokassa (ЛК → Технические настройки)
ROBOKASSA_LOGIN = os.getenv("ROBOKASSA_LOGIN", "").strip()
ROBOKASSA_PASSWORD1 = os.getenv("ROBOKASSA_PASSWORD1", "").strip()
ROBOKASSA_PASSWORD2 = os.getenv("ROBOKASSA_PASSWORD2", "").strip()
ROBOKASSA_HASH = os.getenv("ROBOKASSA_HASH", "md5").strip().lower()  # md5 | sha256 | sha512
ROBOKASSA_IS_TEST = os.getenv("ROBOKASSA_IS_TEST", "0").strip().lower() in ("1", "true", "yes")
ROBOKASSA_TEST_PASSWORD1 = os.getenv("ROBOKASSA_TEST_PASSWORD1", "").strip()
ROBOKASSA_TEST_PASSWORD2 = os.getenv("ROBOKASSA_TEST_PASSWORD2", "").strip()
ROBOKASSA_PAYMENT_URL = os.getenv(
    "ROBOKASSA_PAYMENT_URL",
    "https://auth.robokassa.ru/Merchant/Index.aspx",
)
# Ставка НДС в чеке 54-ФЗ: none (самозанятый) | vat0 | vat10 | vat20 …
ROBOKASSA_RECEIPT_TAX = os.getenv("ROBOKASSA_RECEIPT_TAX", "none").strip() or "none"
ROBOKASSA_RECEIPT_ENABLED = os.getenv("ROBOKASSA_RECEIPT_ENABLED", "1").strip().lower() not in (
    "0", "false", "no",
)

# SS14 Wizard Den OAuth (привязка игрового аккаунта)
SS14_OAUTH_CLIENT_ID = os.getenv("SS14_OAUTH_CLIENT_ID", "")
SS14_OAUTH_CLIENT_SECRET = os.getenv("SS14_OAUTH_CLIENT_SECRET", "")
SS14_OAUTH_REDIRECT_URI = (
    os.getenv("SS14_OAUTH_REDIRECT_URI") or f"{SITE_PUBLIC_URL}/api/ss14/callback"
).strip().rstrip("/")
SS14_OAUTH_AUTHORITY = os.getenv("SS14_OAUTH_AUTHORITY", "https://account.spacestation14.com")

# Реферальная программа
REFERRAL_REFERRER_COINS = int(os.getenv("REFERRAL_REFERRER_COINS", "5"))
REFERRAL_REFEREE_COINS = int(os.getenv("REFERRAL_REFEREE_COINS", "3"))

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