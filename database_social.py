import sqlite3
import datetime
from typing import Optional, List, Dict, Any
import json
import os
SOCIAL_DB_PATH = os.getenv("SOCIAL_DB_PATH", "social.db")

def get_db():
    """Возвращает соединение с SQLite"""
    conn = sqlite3.connect(SOCIAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_social_db():
    """Создает таблицы для соцсети, если их нет"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица пользователей соцсети (связана с игроком через player_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS social_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT UNIQUE NOT NULL,      -- UUID из игровой БД
            user_uuid TEXT UNIQUE NOT NULL,      -- тоже самое, для совместимости
            discord_id TEXT UNIQUE NOT NULL,
            discord_username TEXT,
            discord_avatar TEXT,
            game_nickname TEXT,
            bio TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица постов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_player_id TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_player_id) REFERENCES social_users(player_id) ON DELETE CASCADE
        )
    """)
    
    # Таблица лайков (посты)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, player_id),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES social_users(player_id) ON DELETE CASCADE
        )
    """)
    
    # Таблица комментариев
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_player_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (author_player_id) REFERENCES social_users(player_id) ON DELETE CASCADE
        )
    """)
    
    # Таблица подписок (follower подписан на following)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_player_id TEXT NOT NULL,
            following_player_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_player_id, following_player_id),
            FOREIGN KEY (follower_player_id) REFERENCES social_users(player_id) ON DELETE CASCADE,
            FOREIGN KEY (following_player_id) REFERENCES social_users(player_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS private_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT NOT NULL,
            receiver_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read INTEGER DEFAULT 0,
            FOREIGN KEY (sender_id) REFERENCES social_users(player_id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES social_users(player_id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_token TEXT PRIMARY KEY,
            user_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            player_count INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshot_time 
        ON server_snapshots(timestamp)
    """)
    conn.commit()
    conn.close()

# Инициализация при импорте
init_social_db()

# ---------- Функции работы с пользователями ----------
def get_or_create_social_user(player_id: str, user_uuid: str, discord_id: str, 
                              discord_username: str, discord_avatar: str, game_nickname: str) -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    
    # Проверяем существование
    cursor.execute("SELECT * FROM social_users WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    if row:
        # Обновляем данные (ник, аватар могли измениться)
        cursor.execute("""
            UPDATE social_users 
            SET discord_username = ?, discord_avatar = ?, game_nickname = ?, updated_at = CURRENT_TIMESTAMP
            WHERE player_id = ?
        """, (discord_username, discord_avatar, game_nickname, player_id))
        conn.commit()
        conn.close()
        return dict(row)
    else:
        cursor.execute("""
            INSERT INTO social_users (player_id, user_uuid, discord_id, discord_username, discord_avatar, game_nickname)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (player_id, user_uuid, discord_id, discord_username, discord_avatar, game_nickname))
        conn.commit()
        user_id = cursor.lastrowid
        cursor.execute("SELECT * FROM social_users WHERE id = ?", (user_id,))
        new_row = cursor.fetchone()
        conn.close()
        return dict(new_row)

def get_social_user_by_player_id(player_id: str) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM social_users WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_social_user_by_discord_id(discord_id: str) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM social_users WHERE discord_id = ?", (discord_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_social_user(player_id: str, bio: str = None, game_nickname: str = None) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    if bio is not None:
        fields.append("bio = ?")
        values.append(bio)
    if game_nickname is not None:
        fields.append("game_nickname = ?")
        values.append(game_nickname)
    if not fields:
        return True
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(player_id)
    query = f"UPDATE social_users SET {', '.join(fields)} WHERE player_id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return True

def search_social_users(query: str, limit: int = 50) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    
    if query and len(query.strip()) >= 1:
        cursor.execute("""
            SELECT player_id, game_nickname, discord_username, discord_avatar, discord_id, bio 
            FROM social_users 
            WHERE game_nickname LIKE ? OR discord_username LIKE ?
            ORDER BY game_nickname
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
    else:
        cursor.execute("""
            SELECT player_id, game_nickname, discord_username, discord_avatar, discord_id, bio 
            FROM social_users 
            ORDER BY game_nickname
            LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ---------- Посты ----------
def create_post(author_player_id: str, content: str, image_url: str = None) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO posts (author_player_id, content, image_url)
        VALUES (?, ?, ?)
    """, (author_player_id, content, image_url))
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id

def get_post_by_id(post_id: int) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, su.game_nickname, su.discord_username, su.discord_avatar, su.discord_id,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count
        FROM posts p
        JOIN social_users su ON p.author_player_id = su.player_id
        WHERE p.id = ?
    """, (post_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_feed_posts(player_id: str, limit: int = 30, offset: int = 0) -> List[Dict]:
    """Лента: посты от подписок + свои посты"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, su.game_nickname, su.discord_username, su.discord_avatar, su.discord_id,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND player_id = ?) as liked_by_me
        FROM posts p
        JOIN social_users su ON p.author_player_id = su.player_id
        WHERE p.author_player_id = ? 
           OR p.author_player_id IN (SELECT following_player_id FROM follows WHERE follower_player_id = ?)
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """, (player_id, player_id, player_id, limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_posts(player_id: str, limit: int = 30, offset: int = 0) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, su.game_nickname, su.discord_username, su.discord_avatar, su.discord_id,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND player_id = ?) as liked_by_me
        FROM posts p
        JOIN social_users su ON p.author_player_id = su.player_id
        WHERE p.author_player_id = ?
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """, (player_id, player_id, limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_post(post_id: int, author_player_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ? AND author_player_id = ?", (post_id, author_player_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

# ---------- Лайки ----------
def toggle_like(post_id: int, player_id: str) -> str:
    """Возвращает 'liked' или 'unliked'"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM likes WHERE post_id = ? AND player_id = ?", (post_id, player_id))
    exists = cursor.fetchone()
    if exists:
        cursor.execute("DELETE FROM likes WHERE post_id = ? AND player_id = ?", (post_id, player_id))
        conn.commit()
        conn.close()
        return "unliked"
    else:
        cursor.execute("INSERT INTO likes (post_id, player_id) VALUES (?, ?)", (post_id, player_id))
        conn.commit()
        conn.close()
        return "liked"

def get_like_count(post_id: int) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ---------- Комментарии ----------
def add_comment(post_id: int, author_player_id: str, content: str) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO comments (post_id, author_player_id, content)
        VALUES (?, ?, ?)
    """, (post_id, author_player_id, content))
    conn.commit()
    comment_id = cursor.lastrowid
    conn.close()
    return comment_id

def get_comments(post_id: int, limit: int = 50) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, su.game_nickname, su.discord_username, su.discord_avatar
        FROM comments c
        JOIN social_users su ON c.author_player_id = su.player_id
        WHERE c.post_id = ?
        ORDER BY c.created_at ASC
        LIMIT ?
    """, (post_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_comment(comment_id: int, author_player_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comments WHERE id = ? AND author_player_id = ?", (comment_id, author_player_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

# ---------- Подписки ----------
def follow_user(follower_id: str, following_id: str) -> bool:
    if follower_id == following_id:
        return False
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO follows (follower_player_id, following_player_id)
            VALUES (?, ?)
        """, (follower_id, following_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def unfollow_user(follower_id: str, following_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM follows WHERE follower_player_id = ? AND following_player_id = ?
    """, (follower_id, following_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def is_following(follower_id: str, following_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM follows WHERE follower_player_id = ? AND following_player_id = ?", (follower_id, following_id))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def get_follow_counts(player_id: str) -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM follows WHERE follower_player_id = ?", (player_id,))
    following_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM follows WHERE following_player_id = ?", (player_id,))
    followers_count = cursor.fetchone()[0]
    conn.close()
    return {"following": following_count, "followers": followers_count}

def get_followers(player_id: str, limit: int = 20) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT su.player_id, su.game_nickname, su.discord_username, su.discord_avatar
        FROM follows f
        JOIN social_users su ON f.follower_player_id = su.player_id
        WHERE f.following_player_id = ?
        ORDER BY f.created_at DESC
        LIMIT ?
    """, (player_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_following(player_id: str, limit: int = 20) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT su.player_id, su.game_nickname, su.discord_username, su.discord_avatar
        FROM follows f
        JOIN social_users su ON f.following_player_id = su.player_id
        WHERE f.follower_player_id = ?
        ORDER BY f.created_at DESC
        LIMIT ?
    """, (player_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def send_private_message(sender_id: str, receiver_id: str, content: str) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO private_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
        (sender_id, receiver_id, content)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def get_conversation(user_id: str, other_id: str, limit: int = 50) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM private_messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, other_id, other_id, user_id, limit))
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def get_user_dialogs(user_id: str) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT other_id, MAX(created_at) as last_time, content as last_msg,
               SUM(CASE WHEN sender_id != ? AND read = 0 THEN 1 ELSE 0 END) as unread
        FROM (
            SELECT receiver_id as other_id, created_at, content, read, sender_id
            FROM private_messages WHERE sender_id = ?
            UNION ALL
            SELECT sender_id as other_id, created_at, content, read, sender_id
            FROM private_messages WHERE receiver_id = ?
        ) GROUP BY other_id
        ORDER BY last_time DESC
    """, (user_id, user_id, user_id))
    dialogs = []
    for row in cursor.fetchall():
        d = dict(row)
        # Получаем ник собеседника
        cursor2 = conn.cursor()
        cursor2.execute("SELECT game_nickname FROM social_users WHERE player_id = ?", (d["other_id"],))
        other = cursor2.fetchone()
        d["nickname"] = other["game_nickname"] if other else "Unknown"
        dialogs.append(d)
    conn.close()
    return dialogs

import json
from datetime import datetime

def load_sessions_from_db() -> dict:
    """Загружает все активные сессии в словарь."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT session_token, user_data FROM sessions")
    sessions = {}
    for row in cursor.fetchall():
        sessions[row["session_token"]] = json.loads(row["user_data"])
    conn.close()
    return sessions

def save_session_to_db(session_token: str, data: dict):
    """Сохраняет или обновляет сессию."""
    conn = get_db()
    cursor = conn.cursor()
    user_data_json = json.dumps(data)
    cursor.execute("""
        INSERT INTO sessions (session_token, user_data, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_token) DO UPDATE SET user_data = excluded.user_data
    """, (session_token, user_data_json))
    conn.commit()
    conn.close()

def delete_session_from_db(session_token: str):
    """Удаляет сессию."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
    conn.commit()
    conn.close()

def cleanup_expired_sessions(max_age_days: int = 30):
    """Удаляет сессии старше указанного количества дней."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE created_at < datetime('now', '-' || ? || ' days')", (max_age_days,))
    conn.commit()
    conn.close()