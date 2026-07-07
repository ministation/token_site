import sqlite3
import datetime
from typing import Optional, List, Dict, Any
import json
import os
SOCIAL_DB_PATH = os.getenv("SOCIAL_DB_PATH", "social.db")

_pm_schema_cache: tuple[str, list[str], str | None] | None = None


def get_db():
    """Возвращает соединение с SQLite"""
    conn = sqlite3.connect(SOCIAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(cursor, table: str) -> set[str]:
    return {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}


def _pm_text_columns_from_cols(cols: set[str]) -> list[str]:
    return [c for c in ("content", "message", "text") if c in cols]


def _pm_body_sql(text_cols: list[str]) -> str:
    if not text_cols:
        return "''"
    if len(text_cols) == 1:
        return text_cols[0]
    return f"COALESCE({', '.join(text_cols)})"


def get_pm_table_info() -> tuple[str, list[str], str | None]:
    """Возвращает (имя таблицы, колонки текста, колонка read)."""
    global _pm_schema_cache
    if _pm_schema_cache:
        return _pm_schema_cache

    conn = get_db()
    cursor = conn.cursor()
    for table in ("private_messages", "pm_messages"):
        cols = _table_columns(cursor, table)
        if not cols:
            continue
        
        text_cols = _pm_text_columns_from_cols(cols)
        if not text_cols:
            continue

        read_col = "read" if "read" in cols else ("is_read" if "is_read" in cols else None)

        conn.close()
        _pm_schema_cache = (table, text_cols, read_col)
        return _pm_schema_cache

    conn.close()
    _pm_schema_cache = ("private_messages", ["content"], "read")
    return _pm_schema_cache

def get_social_user_by_user_uuid(user_uuid: str) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM social_users WHERE user_uuid = ? OR player_id = ? LIMIT 1",
        (user_uuid, user_uuid),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_pm_unread_total(user_id: str) -> int:
    table, _, read_col = get_pm_table_info()
    if not read_col:
        return 0
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT COUNT(*) FROM {table} WHERE receiver_id = ? AND COALESCE({read_col}, 0) = 0",
        (user_id,),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return int(count or 0)


def get_feed_latest_by_category() -> Dict[str, Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category,
               MAX(id) AS latest_id,
               MAX(created_at) AS latest_at
        FROM posts
        GROUP BY category
    """)
    rows = {row["category"] or "forum": dict(row) for row in cursor.fetchall()}
    cursor.execute("SELECT MAX(id) AS latest_id, MAX(created_at) AS latest_at FROM posts")
    overall = dict(cursor.fetchone() or {})
    conn.close()
    return {"by_category": rows, "overall": overall}

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
        CREATE TABLE IF NOT EXISTS global_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id TEXT NOT NULL,
            author_nickname TEXT NOT NULL,
            author_avatar TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES social_users(player_id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()
    get_pm_table_info()
    _migrate_schema()


def _migrate_schema():
    conn = get_db()
    cursor = conn.cursor()
    user_cols = _table_columns(cursor, "social_users")
    if "avatar_path" not in user_cols:
        cursor.execute("ALTER TABLE social_users ADD COLUMN avatar_path TEXT")
    if "avatar_custom" not in user_cols:
        cursor.execute("ALTER TABLE social_users ADD COLUMN avatar_custom INTEGER DEFAULT 0")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_admins (
            discord_id TEXT PRIMARY KEY,
            discord_username TEXT,
            granted_by TEXT,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    admin_cols = _table_columns(cursor, "site_admins")
    if "role" not in admin_cols:
        cursor.execute("ALTER TABLE site_admins ADD COLUMN role TEXT DEFAULT 'admin'")
        cursor.execute("UPDATE site_admins SET role = 'admin' WHERE role IS NULL")
    post_cols = _table_columns(cursor, "posts")
    if "category" not in post_cols:
        cursor.execute("ALTER TABLE posts ADD COLUMN category TEXT DEFAULT 'forum'")
        cursor.execute("UPDATE posts SET category = 'forum' WHERE category IS NULL")
    if "topic" not in post_cols:
        cursor.execute("ALTER TABLE posts ADD COLUMN topic TEXT")
    if "title" not in post_cols:
        cursor.execute("ALTER TABLE posts ADD COLUMN title TEXT")
    if "video_url" not in post_cols:
        cursor.execute("ALTER TABLE posts ADD COLUMN video_url TEXT")
    chat_cols = _table_columns(cursor, "global_chat_messages")
    if "image_url" not in chat_cols:
        cursor.execute("ALTER TABLE global_chat_messages ADD COLUMN image_url TEXT")
    pm_table, _, _ = get_pm_table_info()
    pm_cols = _table_columns(cursor, pm_table)
    if "image_url" not in pm_cols:
        cursor.execute(f"ALTER TABLE {pm_table} ADD COLUMN image_url TEXT")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ban_appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ban_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            user_uuid TEXT,
            ckey TEXT,
            appeal_text TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            admin_response TEXT,
            reviewed_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            visitor_key TEXT NOT NULL,
            discord_id TEXT,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_site_visits_at ON site_visits(visited_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_site_visits_key ON site_visits(visitor_key)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rating_removal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id INTEGER NOT NULL,
            admin_uuid TEXT NOT NULL,
            player_uuid TEXT,
            stars INTEGER,
            removed_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Инициализация при импорте
init_social_db()

# ---------- Функции работы с пользователями ----------

def _migrate_user_id_refs(old_id: str, new_id: str):
    """Переносит PM и посты при смене player_id (discord → игровой аккаунт)."""
    if not old_id or old_id == new_id:
        return
    conn = get_db()
    cursor = conn.cursor()
    table, _, _ = get_pm_table_info()
    for col in ("sender_id", "receiver_id"):
        cursor.execute(f"UPDATE {table} SET {col} = ? WHERE {col} = ?", (new_id, old_id))
    cursor.execute("UPDATE posts SET author_player_id = ? WHERE author_player_id = ?", (new_id, old_id))
    cursor.execute("UPDATE likes SET player_id = ? WHERE player_id = ?", (new_id, old_id))
    cursor.execute("UPDATE comments SET author_player_id = ? WHERE author_player_id = ?", (new_id, old_id))
    cursor.execute("UPDATE follows SET follower_player_id = ? WHERE follower_player_id = ?", (new_id, old_id))
    cursor.execute("UPDATE follows SET following_player_id = ? WHERE following_player_id = ?", (new_id, old_id))
    cursor.execute("UPDATE global_chat_messages SET author_id = ? WHERE author_id = ?", (new_id, old_id))
    conn.commit()
    conn.close()


def get_or_create_social_user(player_id: str, user_uuid: str, discord_id: str, 
                              discord_username: str, discord_avatar: str, game_nickname: str) -> Dict:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM social_users WHERE discord_id = ?", (discord_id,))
    row = cursor.fetchone()
    if row:
        old_player_id = row["player_id"]
        cursor.execute("""
            UPDATE social_users 
            SET player_id = ?, user_uuid = ?, discord_username = ?,
                game_nickname = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_id = ?
        """, (player_id, user_uuid, discord_username, game_nickname, discord_id))
        if discord_avatar and not (row["avatar_custom"] if "avatar_custom" in row.keys() else 0):
            cursor.execute(
                "UPDATE social_users SET discord_avatar = ? WHERE discord_id = ?",
                (discord_avatar, discord_id)
            )
        conn.commit()
        if old_player_id != player_id:
            _migrate_user_id_refs(old_player_id, player_id)
        cursor.execute("SELECT * FROM social_users WHERE discord_id = ?", (discord_id,))
        updated = cursor.fetchone()
        conn.close()
        return dict(updated)

    cursor.execute("SELECT * FROM social_users WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE social_users 
            SET discord_id = ?, user_uuid = ?, discord_username = ?, discord_avatar = ?,
                game_nickname = ?, updated_at = CURRENT_TIMESTAMP
            WHERE player_id = ?
        """, (discord_id, user_uuid, discord_username, discord_avatar, game_nickname, player_id))
        conn.commit()
        conn.close()
        return dict(row)

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


def get_social_user_by_discord_username(username: str) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM social_users WHERE LOWER(discord_username) = LOWER(?) LIMIT 1",
        (username.strip().lstrip("@"),)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_avatar(discord_id: str, avatar_path: str,
                       discord_hash: str | None = None, custom: bool | None = None) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    fields = ["avatar_path = ?", "updated_at = CURRENT_TIMESTAMP"]
    values: list = [avatar_path]
    if discord_hash is not None:
        fields.append("discord_avatar = ?")
        values.append(discord_hash)
    if custom is not None:
        fields.append("avatar_custom = ?")
        values.append(1 if custom else 0)
    values.append(discord_id)
    cursor.execute(f"UPDATE social_users SET {', '.join(fields)} WHERE discord_id = ?", values)
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def get_site_staff_role(discord_id: str) -> str | None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM site_admins WHERE discord_id = ?", (discord_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return row["role"] or "admin"


def is_site_admin(discord_id: str) -> bool:
    return get_site_staff_role(discord_id) == "admin"


def is_site_moderator(discord_id: str) -> bool:
    return get_site_staff_role(discord_id) in ("admin", "moderator")


def add_site_staff(discord_id: str, discord_username: str, granted_by: str, role: str = "admin") -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO site_admins (discord_id, discord_username, granted_by, role)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(discord_id) DO UPDATE SET
            discord_username = excluded.discord_username,
            granted_by = excluded.granted_by,
            role = CASE
                WHEN site_admins.role = 'admin' OR excluded.role = 'admin' THEN 'admin'
                ELSE excluded.role
            END
    """, (discord_id, discord_username, granted_by, role))
    conn.commit()
    conn.close()
    return True


def add_site_admin(discord_id: str, discord_username: str, granted_by: str) -> bool:
    return add_site_staff(discord_id, discord_username, granted_by, "admin")


def add_site_moderator(discord_id: str, discord_username: str, granted_by: str) -> bool:
    return add_site_staff(discord_id, discord_username, granted_by, "moderator")


def remove_site_admin(discord_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM site_admins WHERE discord_id = ?", (discord_id,))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def list_site_admins() -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM site_admins ORDER BY created_at ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def seed_moderator_by_username(username: str, granted_by: str = "config") -> bool:
    user = get_social_user_by_discord_username(username)
    if not user:
        return False
    return add_site_moderator(user["discord_id"], user.get("discord_username") or username, granted_by)


def get_ban_appeal_by_id(appeal_id: int) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ban_appeals WHERE id = ?", (appeal_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def seed_admin_by_username(username: str, granted_by: str = "config") -> bool:
    user = get_social_user_by_discord_username(username)
    if not user:
        return False
    return add_site_admin(user["discord_id"], user.get("discord_username") or username, granted_by)


def get_site_stats() -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    stats = {}
    for table, key in [
        ("social_users", "users"),
        ("posts", "posts"),
        ("comments", "comments"),
        ("likes", "likes"),
        ("follows", "follows"),
        ("global_chat_messages", "chat_messages"),
        ("sessions", "sessions"),
        ("site_admins", "admins"),
    ]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[key] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats[key] = 0
    table, _, _ = get_pm_table_info()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        stats["private_messages"] = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        stats["private_messages"] = 0
    conn.close()
    return stats


def record_site_visit(path: str, visitor_key: str, discord_id: str | None = None) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO site_visits (path, visitor_key, discord_id) VALUES (?, ?, ?)",
        (path, visitor_key, discord_id),
    )
    conn.commit()
    conn.close()


def get_visit_stats() -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    stats: Dict = {}
    cursor.execute("SELECT COUNT(*) FROM site_visits")
    stats["visits_total"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT visitor_key) FROM site_visits")
    stats["visitors_total"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM site_visits
        WHERE date(visited_at, '+3 hours') = date('now', '+3 hours')
    """)
    stats["visits_today"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(DISTINCT visitor_key) FROM site_visits
        WHERE date(visited_at, '+3 hours') = date('now', '+3 hours')
    """)
    stats["visitors_today"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM site_visits
        WHERE visited_at >= datetime('now', '-7 days')
    """)
    stats["visits_7d"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(DISTINCT visitor_key) FROM site_visits
        WHERE visited_at >= datetime('now', '-7 days')
    """)
    stats["visitors_7d"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT date(visited_at, '+3 hours') AS day,
               COUNT(*) AS visits,
               COUNT(DISTINCT visitor_key) AS visitors
        FROM site_visits
        WHERE visited_at >= datetime('now', '-7 days')
        GROUP BY day
        ORDER BY day DESC
    """)
    stats["daily"] = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stats


def log_rating_removal(
    rating_id: int,
    admin_uuid: str,
    player_uuid: str | None,
    stars: int,
    removed_by: str,
) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rating_removal_log (rating_id, admin_uuid, player_uuid, stars, removed_by)
        VALUES (?, ?, ?, ?, ?)
    """, (rating_id, admin_uuid, player_uuid, stars, removed_by))
    conn.commit()
    conn.close()


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

def search_social_users(query: str, limit: int = 20) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT player_id, game_nickname, discord_username, discord_avatar, bio 
        FROM social_users 
        WHERE game_nickname LIKE ? OR discord_username LIKE ?
        ORDER BY game_nickname
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ---------- Посты ----------

POST_CATEGORIES = {
    "news": "Новости",
    "forum": "Форум",
    "discussion": "Обсуждения",
}

POST_TOPICS = {
    "gameplay": "Геймплей",
    "suggestions": "Предложения",
    "bugs": "Баги",
    "guides": "Гайды",
    "offtopic": "Оффтоп",
    "other": "Прочее",
}

VALID_CATEGORIES = set(POST_CATEGORIES)
VALID_TOPICS = set(POST_TOPICS)


def create_post(
    author_player_id: str,
    content: str,
    image_url: str = None,
    *,
    category: str = "forum",
    topic: str | None = None,
    title: str | None = None,
    video_url: str | None = None,
) -> int:
    if category not in VALID_CATEGORIES:
        category = "forum"
    if topic and topic not in VALID_TOPICS:
        topic = None
    if category != "discussion":
        topic = None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO posts (author_player_id, content, image_url, video_url, category, topic, title)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (author_player_id, content, image_url, video_url, category, topic, title))
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id

def get_post_by_id(post_id: int) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, su.game_nickname, su.discord_username, su.discord_avatar, su.discord_id,
               su.avatar_path, su.avatar_custom,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count
        FROM posts p
        JOIN social_users su ON p.author_player_id = su.player_id
        WHERE p.id = ?
    """, (post_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_feed_posts(
    player_id: str,
    limit: int = 30,
    offset: int = 0,
    category: str | None = None,
    topic: str | None = None,
) -> List[Dict]:
    """Общая лента: посты по категории и теме."""
    return get_all_posts(player_id, limit, offset, category, topic)


def get_all_posts(
    viewer_id: str | None = None,
    limit: int = 30,
    offset: int = 0,
    category: str | None = None,
    topic: str | None = None,
) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    liked_expr = (
        "EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND player_id = ?)"
        if viewer_id else "0"
    )
    where = []
    params: list = []
    if viewer_id:
        params.append(viewer_id)
    if category:
        if category not in VALID_CATEGORIES:
            category = None
        else:
            where.append("p.category = ?")
            params.append(category)
    if topic:
        if topic not in VALID_TOPICS:
            topic = None
        else:
            where.append("p.topic = ?")
            params.append(topic)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.extend([limit, offset])
    cursor.execute(f"""
        SELECT p.*, su.game_nickname, su.discord_username, su.discord_avatar, su.discord_id,
               su.avatar_path, su.avatar_custom,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               {liked_expr} as liked_by_me
        FROM posts p
        JOIN social_users su ON p.author_player_id = su.player_id
        {where_sql}
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_posts(player_id: str, limit: int = 30, offset: int = 0) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, su.game_nickname, su.discord_username, su.discord_avatar, su.discord_id,
               su.avatar_path, su.avatar_custom,
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


def admin_delete_post(post_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
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
        SELECT c.*, su.game_nickname, su.discord_username, su.discord_avatar, su.avatar_path
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

def send_private_message(sender_id: str, receiver_id: str, content: str, image_url: str | None = None) -> int:
    if sender_id == receiver_id:
        raise ValueError("Нельзя отправить сообщение самому себе")
    table, text_cols, _ = get_pm_table_info()
    conn = get_db()
    cursor = conn.cursor()
    pm_cols = _table_columns(cursor, table)
    insert_cols = ["sender_id", "receiver_id"] + text_cols
    values = [sender_id, receiver_id] + [content] * len(text_cols)
    if "image_url" in pm_cols:
        insert_cols.append("image_url")
        values.append(image_url)
    placeholders = ", ".join(["?"] * len(insert_cols))
    cursor.execute(
        f"INSERT INTO {table} ({', '.join(insert_cols)}) VALUES ({placeholders})",
        values
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id


def get_conversation(user_id: str, other_id: str, limit: int = 50) -> List[Dict]:
    table, text_cols, read_col = get_pm_table_info()
    body_expr = _pm_body_sql(text_cols)
    read_expr = f"COALESCE({read_col}, 0) as read" if read_col else "0 as read"
    conn = get_db()
    cursor = conn.cursor()
    pm_cols = _table_columns(cursor, table)
    image_col = ", image_url" if "image_url" in pm_cols else ", NULL as image_url"
    cursor.execute(f"""
        SELECT id, sender_id, receiver_id, {body_expr} as content, created_at,
               {read_expr}{image_col}
        FROM {table}
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, other_id, other_id, user_id, limit))
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages


def mark_conversation_read(user_id: str, other_id: str) -> int:
    table, _, read_col = get_pm_table_info()
    if not read_col:
        return 0
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE {table} SET {read_col} = 1 WHERE receiver_id = ? AND sender_id = ? AND COALESCE({read_col}, 0) = 0",
        (user_id, other_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected


def get_user_dialogs(user_id: str) -> List[Dict]:
    table, text_cols, read_col = get_pm_table_info()
    body_expr = _pm_body_sql(text_cols)
    read_expr = f"COALESCE({read_col}, 0)" if read_col else "0"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        WITH msgs AS (
            SELECT receiver_id AS other_id, created_at, {body_expr} AS body,
                   {read_expr} AS is_read, sender_id
            FROM {table} WHERE sender_id = ?
            UNION ALL
            SELECT sender_id AS other_id, created_at, {body_expr} AS body,
                   {read_expr} AS is_read, sender_id
            FROM {table} WHERE receiver_id = ?
        ),
        filtered AS (
            SELECT * FROM msgs WHERE other_id != ?
        )
        SELECT
            f.other_id,
            MAX(f.created_at) AS last_time,
            (SELECT body FROM filtered f2
             WHERE f2.other_id = f.other_id
             ORDER BY f2.created_at DESC LIMIT 1) AS last_msg,
            SUM(CASE WHEN f.sender_id != ? AND f.is_read = 0 THEN 1 ELSE 0 END) AS unread
        FROM filtered f
        GROUP BY f.other_id
        ORDER BY last_time DESC
    """, (user_id, user_id, user_id, user_id))
    dialogs = []
    for row in cursor.fetchall():
        d = dict(row)
        cursor.execute(
            "SELECT game_nickname, discord_username FROM social_users WHERE player_id = ?",
            (d["other_id"],)
        )
        other = cursor.fetchone()
        d["nickname"] = (
            other["game_nickname"] or other["discord_username"] if other else "Игрок"
        )
        d["unread"] = int(d.get("unread") or 0)
        dialogs.append(d)
    conn.close()
    return dialogs


def search_message_users(query: str, exclude_player_id: str, limit: int = 100) -> List[Dict]:
    return list_platform_users(exclude_player_id, query, limit, 0)


def list_platform_users(exclude_player_id: str, query: str = "", limit: int = 100, offset: int = 0) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    q = query.strip()
    if len(q) >= 1:
        like = f"%{q}%"
        cursor.execute("""
            SELECT player_id, game_nickname, discord_username, discord_avatar, avatar_path, updated_at
            FROM social_users
            WHERE player_id != ?
              AND (LOWER(game_nickname) LIKE LOWER(?)
                   OR LOWER(discord_username) LIKE LOWER(?))
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (exclude_player_id, like, like, limit, offset))
    else:
        cursor.execute("""
            SELECT player_id, game_nickname, discord_username, discord_avatar, avatar_path, updated_at
            FROM social_users
            WHERE player_id != ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (exclude_player_id, limit, offset))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def list_all_social_users(query: str = "", limit: int = 50, offset: int = 0) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    q = query.strip()
    if len(q) >= 1:
        like = f"%{q}%"
        cursor.execute("""
            SELECT player_id, user_uuid, discord_id, discord_username, game_nickname,
                   avatar_path, created_at, updated_at
            FROM social_users
            WHERE LOWER(game_nickname) LIKE LOWER(?)
               OR LOWER(discord_username) LIKE LOWER(?)
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (like, like, limit, offset))
    else:
        cursor.execute("""
            SELECT player_id, user_uuid, discord_id, discord_username, game_nickname,
                   avatar_path, created_at, updated_at
            FROM social_users
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def count_social_users() -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM social_users")
    n = cursor.fetchone()[0]
    conn.close()
    return n


def create_ban_appeal(ban_id: int, player_id: str, user_uuid: str | None,
                      ckey: str | None, appeal_text: str) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM ban_appeals
        WHERE ban_id = ? AND player_id = ? AND status = 'pending'
    """, (ban_id, player_id))
    if cursor.fetchone():
        conn.close()
        raise ValueError("Обжалование по этому бану уже подано и ожидает рассмотрения")
    cursor.execute("""
        INSERT INTO ban_appeals (ban_id, player_id, user_uuid, ckey, appeal_text)
        VALUES (?, ?, ?, ?, ?)
    """, (ban_id, player_id, user_uuid, ckey, appeal_text.strip()))
    conn.commit()
    appeal_id = cursor.lastrowid
    conn.close()
    return appeal_id


def get_appeals_by_player(player_id: str) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM ban_appeals WHERE player_id = ? ORDER BY created_at DESC
    """, (player_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_appeal_status_map(player_id: str) -> dict[int, dict]:
    appeals = get_appeals_by_player(player_id)
    result = {}
    for a in appeals:
        bid = a["ban_id"]
        if bid not in result or a["created_at"] > result[bid]["created_at"]:
            result[bid] = a
    return result


def list_ban_appeals(status: str | None = None, limit: int = 50, offset: int = 0) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    if status:
        cursor.execute("""
            SELECT * FROM ban_appeals WHERE status = ?
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (status, limit, offset))
    else:
        cursor.execute("""
            SELECT * FROM ban_appeals ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_ban_appeal(appeal_id: int, status: str, admin_response: str, reviewed_by: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE ban_appeals
        SET status = ?, admin_response = ?, reviewed_by = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, admin_response, reviewed_by, appeal_id))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def add_global_chat_message(author_id: str, author_nickname: str,
                            author_avatar: str | None, content: str,
                            image_url: str | None = None) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cols = _table_columns(cursor, "global_chat_messages")
    if "image_url" in cols:
        cursor.execute("""
            INSERT INTO global_chat_messages (author_id, author_nickname, author_avatar, content, image_url)
            VALUES (?, ?, ?, ?, ?)
        """, (author_id, author_nickname, author_avatar, content, image_url))
    else:
        cursor.execute("""
            INSERT INTO global_chat_messages (author_id, author_nickname, author_avatar, content)
            VALUES (?, ?, ?, ?)
        """, (author_id, author_nickname, author_avatar, content))
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id


def get_global_chat_messages(limit: int = 100, after_id: int = 0) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    if after_id:
        cursor.execute("""
            SELECT * FROM global_chat_messages
            WHERE id > ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (after_id, limit))
    else:
        cursor.execute("""
            SELECT * FROM global_chat_messages
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

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