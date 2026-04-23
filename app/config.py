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

# Банк
BANK_DEPOSIT_MIN = int(os.getenv("BANK_DEPOSIT_MIN", "10"))
BANK_DEPOSIT_RATE = int(os.getenv("BANK_DEPOSIT_RATE", "20"))
BANK_DEPOSIT_DAYS = int(os.getenv("BANK_DEPOSIT_DAYS", "7"))
BANK_LOAN_MAX = int(os.getenv("BANK_LOAN_MAX", "50"))
BANK_LOAN_RATE = int(os.getenv("BANK_LOAN_RATE", "30"))
BANK_LOAN_DAYS = int(os.getenv("BANK_LOAN_DAYS", "7"))

# Лотерея и переводы
LOTTERY_COST = int(os.getenv("LOTTERY_COST", "5"))
MIN_TRANSFER = int(os.getenv("MIN_TRANSFER", "1"))
TRANSFER_COOLDOWN = int(os.getenv("TRANSFER_COOLDOWN", "60"))

# Чат
MAX_CHAT_MESSAGES = int(os.getenv("MAX_CHAT_MESSAGES", "100"))

# Сервер
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8067"))

# Файлы и загрузки
SESSIONS_FILE = os.getenv("SESSIONS_FILE", "sessions.json")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)