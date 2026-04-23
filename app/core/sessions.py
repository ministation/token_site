import json
import os
import secrets
import datetime
from app.config import SESSIONS_FILE

# Глобальное хранилище сессий
user_sessions: dict = {}


def load_sessions():
    global user_sessions
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r') as f:
                user_sessions = json.load(f)
        except Exception:
            user_sessions = {}
    else:
        user_sessions = {}


def save_sessions():
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(user_sessions, f, indent=2, default=str)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def get_session(session_token: str) -> dict | None:
    return user_sessions.get(session_token)


def set_session(session_token: str, data: dict):
    user_sessions[session_token] = data
    save_sessions()


def delete_session(session_token: str):
    user_sessions.pop(session_token, None)
    save_sessions()