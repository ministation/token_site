import secrets
import database_social as social_db

# Глобальный кэш сессий (для быстрого доступа без частых обращений к БД)
# Заполняется при старте и поддерживается в актуальном состоянии.
user_sessions: dict = {}

def load_sessions():
    """Загружает сессии из БД в память (вызывается при старте)."""
    global user_sessions
    user_sessions = social_db.load_sessions_from_db()

def generate_session_token() -> str:
    return secrets.token_urlsafe(32)

def get_session(session_token: str) -> dict | None:
    # Сначала ищем в кэше, если нет – пробуем загрузить из БД (на случай рассинхронизации)
    if session_token in user_sessions:
        return user_sessions[session_token]
    # Запасной вариант: загрузить напрямую (может быть, другой процесс обновил)
    all_sessions = social_db.load_sessions_from_db()
    return all_sessions.get(session_token)

def set_session(session_token: str, data: dict):
    user_sessions[session_token] = data
    social_db.save_session_to_db(session_token, data)

def delete_session(session_token: str):
    user_sessions.pop(session_token, None)
    social_db.delete_session_from_db(session_token)