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
    if "last_seen_at" not in user_cols:
        cursor.execute("ALTER TABLE social_users ADD COLUMN last_seen_at TIMESTAMP")
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_content_makers (
            discord_id TEXT PRIMARY KEY,
            discord_username TEXT,
            granted_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_time_keepers (
            discord_id TEXT PRIMARY KEY,
            discord_username TEXT,
            granted_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wiki_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            visitor_key TEXT NOT NULL,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_wiki_visits_at ON wiki_visits(visited_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_wiki_visits_key ON wiki_visits(visitor_key)
    """)
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
        CREATE TABLE IF NOT EXISTS wiki_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            visitor_key TEXT NOT NULL,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_wiki_visits_at ON wiki_visits(visited_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_wiki_visits_key ON wiki_visits(visitor_key)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cdn_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            fork TEXT NOT NULL,
            path TEXT,
            version TEXT,
            platform TEXT,
            visitor_key TEXT,
            bytes_sent INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cdn_events_at ON cdn_events(created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cdn_events_type ON cdn_events(event_type)
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compensation_giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount INTEGER NOT NULL,
            ends_at TIMESTAMP NOT NULL,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compensation_claims (
            giveaway_id INTEGER NOT NULL,
            user_uuid TEXT NOT NULL,
            claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (giveaway_id, user_uuid),
            FOREIGN KEY (giveaway_id) REFERENCES compensation_giveaways(id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_compensation_giveaways_ends
        ON compensation_giveaways(ends_at DESC)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT,
            contact TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            admin_response TEXT,
            reviewed_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_support_tickets_status
        ON support_tickets(status, created_at DESC)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            author_type TEXT NOT NULL,
            author_id TEXT,
            author_name TEXT,
            content TEXT NOT NULL DEFAULT '',
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stm_ticket
        ON support_ticket_messages(ticket_id, created_at)
    """)
    # One-shot backfill: old tickets → first user (+ staff) messages
    cursor.execute("""
        SELECT t.id, t.player_id, t.body, t.admin_response, t.reviewed_by,
               t.created_at, t.updated_at
        FROM support_tickets t
        WHERE NOT EXISTS (
            SELECT 1 FROM support_ticket_messages m WHERE m.ticket_id = t.id
        )
    """)
    for row in cursor.fetchall():
        tid = row["id"]
        body = (row["body"] or "").strip()
        if body:
            cursor.execute("""
                INSERT INTO support_ticket_messages
                    (ticket_id, author_type, author_id, author_name, content, created_at)
                VALUES (?, 'user', ?, NULL, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """, (tid, row["player_id"], body, row["created_at"]))
        admin_resp = (row["admin_response"] or "").strip()
        if admin_resp:
            cursor.execute("""
                INSERT INTO support_ticket_messages
                    (ticket_id, author_type, author_id, author_name, content, created_at)
                VALUES (?, 'staff', ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """, (tid, row["reviewed_by"], row["reviewed_by"] or "Админ",
                  admin_resp, row["updated_at"] or row["created_at"]))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donation_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL UNIQUE,
            tier_id INTEGER NOT NULL,
            tier_name TEXT NOT NULL,
            amount_rub INTEGER NOT NULL,
            currency TEXT DEFAULT 'RUB',
            payment_method INTEGER,
            status TEXT DEFAULT 'pending',
            player_id TEXT,
            discord_id TEXT,
            contact TEXT,
            redirect_url TEXT,
            payload TEXT,
            raw_callback TEXT,
            product_type TEXT DEFAULT 'tier',
            coins_amount INTEGER DEFAULT 0,
            game_user_uuid TEXT,
            fulfilled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_donation_orders_status
        ON donation_orders(status, created_at DESC)
    """)
    don_cols = _table_columns(cursor, "donation_orders")
    if "product_type" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN product_type TEXT DEFAULT 'tier'")
    if "coins_amount" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN coins_amount INTEGER DEFAULT 0")
    if "game_user_uuid" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN game_user_uuid TEXT")
    if "fulfilled" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN fulfilled INTEGER DEFAULT 0")
    if "receipt_uuid" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN receipt_uuid TEXT")
    if "receipt_url" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN receipt_url TEXT")
    if "receipt_status" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN receipt_status TEXT")
    if "receipt_error" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN receipt_error TEXT")
    if "receipt_issued_at" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN receipt_issued_at TIMESTAMP")
    if "receipt_pdf_url" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN receipt_pdf_url TEXT")
    if "receipt_pm_sent" not in don_cols:
        cursor.execute("ALTER TABLE donation_orders ADD COLUMN receipt_pm_sent INTEGER DEFAULT 0")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sponsorships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_transaction_id TEXT UNIQUE,
            player_id TEXT,
            discord_id TEXT,
            game_user_uuid TEXT,
            contact TEXT,
            tier_id INTEGER NOT NULL,
            tier_name TEXT NOT NULL,
            amount_rub INTEGER NOT NULL,
            coins_granted INTEGER DEFAULT 0,
            starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ends_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sponsorships_player
        ON sponsorships(player_id, ends_at DESC)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donation_discounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            percent INTEGER NOT NULL,
            scope TEXT NOT NULL DEFAULT 'all',
            target_id INTEGER,
            badge_text TEXT,
            beneficiary_player_id TEXT,
            beneficiary_discord_id TEXT,
            starts_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ends_at TIMESTAMP NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    dd_cols = _table_columns(cursor, "donation_discounts")
    if "beneficiary_player_id" not in dd_cols:
        cursor.execute("ALTER TABLE donation_discounts ADD COLUMN beneficiary_player_id TEXT")
    if "beneficiary_discord_id" not in dd_cols:
        cursor.execute("ALTER TABLE donation_discounts ADD COLUMN beneficiary_discord_id TEXT")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_donation_discounts_active
        ON donation_discounts(active, starts_at, ends_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_donation_discounts_beneficiary
        ON donation_discounts(beneficiary_player_id, active)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_bans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL,
            player_id TEXT,
            reason TEXT NOT NULL,
            banned_by_discord_id TEXT,
            banned_by_username TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            lifted_at TIMESTAMP,
            lifted_by TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_site_bans_discord_active
        ON site_bans(discord_id, active)
    """)
    user_cols = _table_columns(cursor, "social_users")
    if "referral_code" not in user_cols:
        cursor.execute("ALTER TABLE social_users ADD COLUMN referral_code TEXT")
    if "referred_by_code" not in user_cols:
        cursor.execute("ALTER TABLE social_users ADD COLUMN referred_by_code TEXT")
    if "referral_prompt_done" not in user_cols:
        cursor.execute("ALTER TABLE social_users ADD COLUMN referral_prompt_done INTEGER DEFAULT 0")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_social_users_referral_code
        ON social_users(referral_code)
        WHERE referral_code IS NOT NULL AND referral_code != ''
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referral_pending_coins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_referral_pending_discord
        ON referral_pending_coins(discord_id)
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
                              discord_username: str, discord_avatar: str, game_nickname: str,
                              *, return_created: bool = False):
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
        result = dict(updated)
        return (result, False) if return_created else result

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
        result = dict(row)
        return (result, False) if return_created else result

    cursor.execute("""
        INSERT INTO social_users (player_id, user_uuid, discord_id, discord_username, discord_avatar, game_nickname)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_id, user_uuid, discord_id, discord_username, discord_avatar, game_nickname))
    conn.commit()
    user_id = cursor.lastrowid
    cursor.execute("SELECT * FROM social_users WHERE id = ?", (user_id,))
    new_row = cursor.fetchone()
    conn.close()
    result = dict(new_row)
    return (result, True) if return_created else result


def set_referral_code(discord_id: str, code: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE social_users SET referral_code = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE discord_id = ? AND (referral_code IS NULL OR referral_code = '')",
            (code, discord_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


def get_social_user_by_referral_code(code: str) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM social_users WHERE UPPER(referral_code) = UPPER(?) LIMIT 1",
        (code.strip(),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def mark_referral_used(referred_discord_id: str, code: str, referrer_discord_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT referred_by_code FROM social_users WHERE discord_id = ?",
        (referred_discord_id,),
    )
    row = cursor.fetchone()
    if not row or row["referred_by_code"]:
        conn.close()
        return False
    cursor.execute(
        """
        UPDATE social_users
        SET referred_by_code = ?, referral_prompt_done = 1, updated_at = CURRENT_TIMESTAMP
        WHERE discord_id = ? AND referred_by_code IS NULL
        """,
        (code.upper(), referred_discord_id),
    )
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def needs_referral_prompt(discord_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT referred_by_code, referral_prompt_done FROM social_users WHERE discord_id = ?",
        (discord_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    return not row["referred_by_code"] and not row["referral_prompt_done"]


def complete_referral_prompt(discord_id: str) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE social_users SET referral_prompt_done = 1, updated_at = CURRENT_TIMESTAMP "
        "WHERE discord_id = ?",
        (discord_id,),
    )
    conn.commit()
    conn.close()


def get_referral_stats(discord_id: str) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM social_users WHERE referred_by_code IN "
        "(SELECT referral_code FROM social_users WHERE discord_id = ?)",
        (discord_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return {"count": int(row["cnt"]) if row else 0}


def get_global_referral_stats() -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM social_users "
        "WHERE referred_by_code IS NOT NULL AND referred_by_code != ''"
    )
    referrals_total = int(cursor.fetchone()["cnt"])
    cursor.execute(
        """
        SELECT COUNT(DISTINCT u.discord_id) AS cnt
        FROM social_users u
        WHERE EXISTS (
            SELECT 1 FROM social_users r
            WHERE r.referred_by_code = u.referral_code
              AND r.referred_by_code IS NOT NULL
              AND r.referred_by_code != ''
        )
        """
    )
    referrers_active = int(cursor.fetchone()["cnt"])
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM referral_pending_coins")
    pending_coins = int(cursor.fetchone()["s"])
    conn.close()
    return {
        "referrals_total": referrals_total,
        "referrers_active": referrers_active,
        "pending_coins": pending_coins,
    }


def add_pending_referral_coins(discord_id: str, amount: int, reason: str) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO referral_pending_coins (discord_id, amount, reason) VALUES (?, ?, ?)",
        (discord_id, amount, reason),
    )
    conn.commit()
    conn.close()


def pop_pending_referral_coins(discord_id: str) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, amount, reason FROM referral_pending_coins WHERE discord_id = ? ORDER BY id",
        (discord_id,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    if rows:
        ids = [r["id"] for r in rows]
        cursor.execute(
            f"DELETE FROM referral_pending_coins WHERE id IN ({','.join('?' * len(ids))})",
            ids,
        )
        conn.commit()
    conn.close()
    return rows

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


def is_content_maker(discord_id: str) -> bool:
    if not discord_id:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM site_content_makers WHERE discord_id = ? LIMIT 1", (discord_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_content_maker_source(discord_id: str) -> str | None:
    if not discord_id:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT granted_by FROM site_content_makers WHERE discord_id = ?", (discord_id,))
    row = cursor.fetchone()
    conn.close()
    return row["granted_by"] if row else None


def add_content_maker(discord_id: str, discord_username: str, granted_by: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO site_content_makers (discord_id, discord_username, granted_by)
        VALUES (?, ?, ?)
        ON CONFLICT(discord_id) DO UPDATE SET
            discord_username = excluded.discord_username,
            granted_by = CASE
                WHEN site_content_makers.granted_by IN ('admin', 'manual') THEN site_content_makers.granted_by
                ELSE excluded.granted_by
            END
    """, (discord_id, discord_username, granted_by))
    conn.commit()
    conn.close()
    return True


def remove_content_maker(discord_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM site_content_makers WHERE discord_id = ?", (discord_id,))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def list_content_makers() -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM site_content_makers ORDER BY created_at ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def is_time_keeper(discord_id: str) -> bool:
    if not discord_id:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM site_time_keepers WHERE discord_id = ? LIMIT 1", (discord_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_time_keeper_source(discord_id: str) -> str | None:
    if not discord_id:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT granted_by FROM site_time_keepers WHERE discord_id = ?", (discord_id,))
    row = cursor.fetchone()
    conn.close()
    return row["granted_by"] if row else None


def add_time_keeper(discord_id: str, discord_username: str, granted_by: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO site_time_keepers (discord_id, discord_username, granted_by)
        VALUES (?, ?, ?)
        ON CONFLICT(discord_id) DO UPDATE SET
            discord_username = excluded.discord_username,
            granted_by = CASE
                WHEN site_time_keepers.granted_by IN ('admin', 'manual') THEN site_time_keepers.granted_by
                ELSE excluded.granted_by
            END
    """, (discord_id, discord_username, granted_by))
    conn.commit()
    conn.close()
    return True


def remove_time_keeper(discord_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM site_time_keepers WHERE discord_id = ?", (discord_id,))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def list_time_keepers() -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM site_time_keepers ORDER BY created_at ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def list_all_social_users() -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id, discord_username FROM social_users WHERE discord_id IS NOT NULL")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


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


def seed_content_maker_by_username(username: str, granted_by: str = "config") -> bool:
    user = get_social_user_by_discord_username(username)
    if not user:
        return False
    return add_content_maker(user["discord_id"], user.get("discord_username") or username, granted_by)


def seed_time_keeper_by_username(username: str, granted_by: str = "config") -> bool:
    user = get_social_user_by_discord_username(username)
    if not user:
        return False
    return add_time_keeper(user["discord_id"], user.get("discord_username") or username, granted_by)


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


def record_wiki_visit(path: str, visitor_key: str) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO wiki_visits (path, visitor_key) VALUES (?, ?)",
        (path, visitor_key),
    )
    conn.commit()
    conn.close()


def get_wiki_stats() -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    stats: Dict = {}
    cursor.execute("SELECT COUNT(*) FROM wiki_visits")
    stats["visits_total"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT visitor_key) FROM wiki_visits")
    stats["visitors_total"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM wiki_visits
        WHERE date(visited_at, '+3 hours') = date('now', '+3 hours')
    """)
    stats["visits_today"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(DISTINCT visitor_key) FROM wiki_visits
        WHERE date(visited_at, '+3 hours') = date('now', '+3 hours')
    """)
    stats["visitors_today"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM wiki_visits
        WHERE visited_at >= datetime('now', '-7 days')
    """)
    stats["visits_7d"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(DISTINCT visitor_key) FROM wiki_visits
        WHERE visited_at >= datetime('now', '-7 days')
    """)
    stats["visitors_7d"] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT date(visited_at, '+3 hours') AS day,
               COUNT(*) AS visits,
               COUNT(DISTINCT visitor_key) AS visitors
        FROM wiki_visits
        WHERE visited_at >= datetime('now', '-7 days')
        GROUP BY day
        ORDER BY day DESC
    """)
    stats["daily"] = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stats


def record_cdn_event(
    event_type: str,
    fork: str,
    *,
    path: str | None = None,
    version: str | None = None,
    platform: str | None = None,
    visitor_key: str | None = None,
    bytes_sent: int | None = None,
) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO cdn_events (event_type, fork, path, version, platform, visitor_key, bytes_sent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_type, fork, path, version, platform, visitor_key, bytes_sent),
    )
    conn.commit()
    conn.close()


def get_cdn_stats() -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    stats: Dict = {}

    def _count(where: str = "", params: tuple = ()) -> int:
        cursor.execute(f"SELECT COUNT(*) FROM cdn_events {where}", params)
        return cursor.fetchone()[0]

    def _distinct_visitors(where: str = "", params: tuple = ()) -> int:
        clause = where if where else "WHERE visitor_key IS NOT NULL"
        if where and "visitor_key" not in where:
            clause = f"{where} AND visitor_key IS NOT NULL"
        cursor.execute(f"SELECT COUNT(DISTINCT visitor_key) FROM cdn_events {clause}", params)
        return cursor.fetchone()[0]

    stats["page_visits_total"] = _count("WHERE event_type = 'page_visit'")
    stats["page_visits_today"] = _count(
        "WHERE event_type = 'page_visit' AND date(created_at, '+3 hours') = date('now', '+3 hours')"
    )
    stats["page_visitors_today"] = _distinct_visitors(
        "WHERE event_type = 'page_visit' AND date(created_at, '+3 hours') = date('now', '+3 hours')"
    )
    stats["page_visits_7d"] = _count(
        "WHERE event_type = 'page_visit' AND created_at >= datetime('now', '-7 days')"
    )
    stats["page_visitors_7d"] = _distinct_visitors(
        "WHERE event_type = 'page_visit' AND created_at >= datetime('now', '-7 days')"
    )

    stats["downloads_total"] = _count("WHERE event_type = 'server_download'")
    stats["downloads_today"] = _count(
        "WHERE event_type = 'server_download' AND date(created_at, '+3 hours') = date('now', '+3 hours')"
    )
    stats["downloads_7d"] = _count(
        "WHERE event_type = 'server_download' AND created_at >= datetime('now', '-7 days')"
    )

    cursor.execute("""
        SELECT date(created_at, '+3 hours') AS day,
               SUM(CASE WHEN event_type = 'page_visit' THEN 1 ELSE 0 END) AS page_visits,
               SUM(CASE WHEN event_type = 'server_download' THEN 1 ELSE 0 END) AS downloads
        FROM cdn_events
        WHERE created_at >= datetime('now', '-7 days')
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
        SELECT su.player_id, su.game_nickname, su.discord_username, su.discord_id,
               su.discord_avatar, su.avatar_path, su.avatar_custom
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
        SELECT su.player_id, su.game_nickname, su.discord_username, su.discord_id,
               su.discord_avatar, su.avatar_path, su.avatar_custom
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
            SELECT player_id, game_nickname, discord_username, discord_id, discord_avatar, avatar_path,
                   updated_at, last_seen_at
            FROM social_users
            WHERE player_id != ?
              AND (LOWER(game_nickname) LIKE LOWER(?)
                   OR LOWER(discord_username) LIKE LOWER(?))
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (exclude_player_id, like, like, limit, offset))
    else:
        cursor.execute("""
            SELECT player_id, game_nickname, discord_username, discord_id, discord_avatar, avatar_path,
                   updated_at, last_seen_at
            FROM social_users
            WHERE player_id != ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (exclude_player_id, limit, offset))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def touch_presence(player_id: str) -> None:
    if not player_id:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE social_users SET last_seen_at = CURRENT_TIMESTAMP WHERE player_id = ?",
        (player_id,),
    )
    conn.commit()
    conn.close()


def get_presence_map(player_ids: List[str]) -> Dict[str, Optional[str]]:
    ids = [pid for pid in player_ids if pid]
    if not ids:
        return {}
    conn = get_db()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    cursor.execute(
        f"SELECT player_id, last_seen_at FROM social_users WHERE player_id IN ({placeholders})",
        ids,
    )
    out = {row["player_id"]: row["last_seen_at"] for row in cursor.fetchall()}
    conn.close()
    return out


def list_all_social_users(query: str = "", limit: int = 50, offset: int = 0) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    q = query.strip()
    if len(q) >= 1:
        like = f"%{q}%"
        cursor.execute("""
            SELECT player_id, user_uuid, discord_id, discord_username, game_nickname,
                   avatar_path, created_at, updated_at, last_seen_at
            FROM social_users
            WHERE LOWER(game_nickname) LIKE LOWER(?)
               OR LOWER(discord_username) LIKE LOWER(?)
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (like, like, limit, offset))
    else:
        cursor.execute("""
            SELECT player_id, user_uuid, discord_id, discord_username, game_nickname,
                   avatar_path, created_at, updated_at, last_seen_at
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


def create_support_ticket(contact: str, subject: str, body: str, player_id: str | None = None) -> int:
    conn = get_db()
    cursor = conn.cursor()
    body_clean = body.strip()
    cursor.execute("""
        INSERT INTO support_tickets (player_id, contact, subject, body)
        VALUES (?, ?, ?, ?)
    """, (player_id, contact.strip(), subject.strip(), body_clean))
    ticket_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO support_ticket_messages
            (ticket_id, author_type, author_id, author_name, content)
        VALUES (?, 'user', ?, NULL, ?)
    """, (ticket_id, player_id, body_clean))
    conn.commit()
    conn.close()
    return ticket_id


def list_support_tickets(status: str | None = None, limit: int = 50, offset: int = 0) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    st = (status or "").strip()
    if st:
        cursor.execute("""
            SELECT t.*,
                (SELECT content FROM support_ticket_messages m
                 WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_message,
                (SELECT author_type FROM support_ticket_messages m
                 WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_author_type,
                (SELECT created_at FROM support_ticket_messages m
                 WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_message_at
            FROM support_tickets t
            WHERE t.status = ?
            ORDER BY COALESCE(
                (SELECT created_at FROM support_ticket_messages m
                 WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1),
                t.updated_at, t.created_at
            ) DESC
            LIMIT ? OFFSET ?
        """, (st, limit, offset))
    else:
        cursor.execute("""
            SELECT t.*,
                (SELECT content FROM support_ticket_messages m
                 WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_message,
                (SELECT author_type FROM support_ticket_messages m
                 WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_author_type,
                (SELECT created_at FROM support_ticket_messages m
                 WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_message_at
            FROM support_tickets t
            ORDER BY COALESCE(
                (SELECT created_at FROM support_ticket_messages m
                 WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1),
                t.updated_at, t.created_at
            ) DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def list_support_tickets_by_player(player_id: str, limit: int = 30) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*,
            (SELECT content FROM support_ticket_messages m
             WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_message,
            (SELECT author_type FROM support_ticket_messages m
             WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_author_type,
            (SELECT created_at FROM support_ticket_messages m
             WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_message_at
        FROM support_tickets t
        WHERE t.player_id = ?
        ORDER BY COALESCE(
            (SELECT created_at FROM support_ticket_messages m
             WHERE m.ticket_id = t.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1),
            t.updated_at, t.created_at
        ) DESC
        LIMIT ?
    """, (player_id, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_support_ticket(ticket_id: int) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def list_support_ticket_messages(ticket_id: int, limit: int = 200) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, ticket_id, author_type, author_id, author_name, content, image_url, created_at
        FROM support_ticket_messages
        WHERE ticket_id = ?
        ORDER BY created_at ASC, id ASC
        LIMIT ?
    """, (ticket_id, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def add_support_ticket_message(
    ticket_id: int,
    author_type: str,
    content: str,
    author_id: str | None = None,
    author_name: str | None = None,
    image_url: str | None = None,
    new_status: str | None = None,
) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO support_ticket_messages
            (ticket_id, author_type, author_id, author_name, content, image_url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        ticket_id,
        author_type,
        author_id,
        author_name,
        (content or "").strip(),
        image_url,
    ))
    msg_id = cursor.lastrowid
    if author_type == "staff":
        cursor.execute("""
            UPDATE support_tickets
            SET admin_response = ?, reviewed_by = COALESCE(?, reviewed_by),
                status = COALESCE(?, status),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, ((content or "").strip() or None, author_name or author_id, new_status, ticket_id))
    else:
        cursor.execute("""
            UPDATE support_tickets
            SET status = COALESCE(?, status),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status or "open", ticket_id))
    conn.commit()
    conn.close()
    return msg_id


def update_support_ticket(ticket_id: int, status: str, admin_response: str, reviewed_by: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE support_tickets
        SET status = ?, admin_response = ?, reviewed_by = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, admin_response, reviewed_by, ticket_id))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def set_support_ticket_status(ticket_id: int, status: str, reviewed_by: str | None = None) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    if reviewed_by:
        cursor.execute("""
            UPDATE support_tickets
            SET status = ?, reviewed_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, reviewed_by, ticket_id))
    else:
        cursor.execute("""
            UPDATE support_tickets
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, ticket_id))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def create_donation_order(
    transaction_id: str,
    tier_id: int,
    tier_name: str,
    amount_rub: int,
    payment_method: int | None = None,
    player_id: str | None = None,
    discord_id: str | None = None,
    contact: str | None = None,
    redirect_url: str | None = None,
    payload: str | None = None,
    product_type: str = "tier",
    coins_amount: int = 0,
    game_user_uuid: str | None = None,
) -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO donation_orders (
            transaction_id, tier_id, tier_name, amount_rub, payment_method,
            player_id, discord_id, contact, redirect_url, payload, status,
            product_type, coins_amount, game_user_uuid, fulfilled
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, 0)
    """, (
        transaction_id, tier_id, tier_name, amount_rub, payment_method,
        player_id, discord_id, contact, redirect_url, payload,
        product_type or "tier", int(coins_amount or 0), game_user_uuid,
    ))
    conn.commit()
    order_id = cursor.lastrowid
    cursor.execute("SELECT * FROM donation_orders WHERE id = ?", (order_id,))
    row = dict(cursor.fetchone())
    conn.close()
    return row


def get_donation_order_by_tx(transaction_id: str) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donation_orders WHERE transaction_id = ?", (transaction_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_donation_order_by_id(order_id: int) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donation_orders WHERE id = ?", (int(order_id),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def mark_donation_fulfilled(transaction_id: str) -> bool:
    """Атомарно ставит fulfilled=1 только если ещё не выдано. True = мы захватили заказ."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE donation_orders
        SET fulfilled = 1, updated_at = CURRENT_TIMESTAMP
        WHERE transaction_id = ? AND COALESCE(fulfilled, 0) = 0 AND status = 'confirmed'
    """, (transaction_id,))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def update_donation_order(
    transaction_id: str,
    *,
    status: str | None = None,
    redirect_url: str | None = None,
    raw_callback: str | None = None,
    fulfilled: int | None = None,
    payload: str | None = None,
    receipt_uuid: str | None = None,
    receipt_url: str | None = None,
    receipt_status: str | None = None,
    receipt_error: str | None = None,
    receipt_issued_at: str | None = None,
    receipt_pdf_url: str | None = None,
    receipt_pm_sent: int | None = None,
) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    sets = ["updated_at = CURRENT_TIMESTAMP"]
    params: list = []
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if redirect_url is not None:
        sets.append("redirect_url = ?")
        params.append(redirect_url)
    if raw_callback is not None:
        sets.append("raw_callback = ?")
        params.append(raw_callback)
    if fulfilled is not None:
        sets.append("fulfilled = ?")
        params.append(int(fulfilled))
    if payload is not None:
        sets.append("payload = ?")
        params.append(payload)
    if receipt_uuid is not None:
        sets.append("receipt_uuid = ?")
        params.append(receipt_uuid)
    if receipt_url is not None:
        sets.append("receipt_url = ?")
        params.append(receipt_url)
    if receipt_status is not None:
        sets.append("receipt_status = ?")
        params.append(receipt_status)
    if receipt_error is not None:
        sets.append("receipt_error = ?")
        params.append(receipt_error)
    if receipt_issued_at is not None:
        sets.append("receipt_issued_at = ?")
        params.append(receipt_issued_at)
    if receipt_pdf_url is not None:
        sets.append("receipt_pdf_url = ?")
        params.append(receipt_pdf_url)
    if receipt_pm_sent is not None:
        sets.append("receipt_pm_sent = ?")
        params.append(int(receipt_pm_sent))
    params.append(transaction_id)
    cursor.execute(
        f"UPDATE donation_orders SET {', '.join(sets)} WHERE transaction_id = ?",
        params,
    )
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def list_donation_orders(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    limit = min(max(int(limit), 1), 100)
    offset = max(int(offset), 0)
    if status:
        cursor.execute(
            """
            SELECT * FROM donation_orders
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (status, limit, offset),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM donation_orders
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def donation_stats(
    *,
    date_from: str,
    date_to: str,
) -> dict:
    """Метрики по confirmed-донатом за период [date_from, date_to] (UTC/локальные строки SQLite)."""
    conn = get_db()
    cursor = conn.cursor()
    # inclusive day range via timestamps
    start = f"{date_from} 00:00:00"
    end = f"{date_to} 23:59:59"

    cursor.execute(
        """
        SELECT
            COUNT(*) AS orders_count,
            COALESCE(SUM(amount_rub), 0) AS total_rub,
            COUNT(DISTINCT CASE
                WHEN discord_id IS NOT NULL AND discord_id != '' THEN discord_id
                WHEN player_id IS NOT NULL AND player_id != '' THEN player_id
                ELSE NULL
            END) AS unique_donors
        FROM donation_orders
        WHERE status = 'confirmed'
          AND datetime(created_at) >= datetime(?)
          AND datetime(created_at) <= datetime(?)
        """,
        (start, end),
    )
    totals = dict(cursor.fetchone() or {})

    cursor.execute(
        """
        SELECT product_type,
               COUNT(*) AS cnt,
               COALESCE(SUM(amount_rub), 0) AS rub
        FROM donation_orders
        WHERE status = 'confirmed'
          AND datetime(created_at) >= datetime(?)
          AND datetime(created_at) <= datetime(?)
        GROUP BY product_type
        ORDER BY rub DESC
        """,
        (start, end),
    )
    by_product = [dict(r) for r in cursor.fetchall()]

    cursor.execute(
        """
        SELECT tier_id, tier_name,
               COUNT(*) AS cnt,
               COALESCE(SUM(amount_rub), 0) AS rub
        FROM donation_orders
        WHERE status = 'confirmed'
          AND datetime(created_at) >= datetime(?)
          AND datetime(created_at) <= datetime(?)
        GROUP BY tier_id, tier_name
        ORDER BY rub DESC
        """,
        (start, end),
    )
    by_item = [dict(r) for r in cursor.fetchall()]

    cursor.execute(
        """
        SELECT
            COALESCE(NULLIF(discord_id, ''), NULLIF(player_id, ''), 'unknown') AS donor_key,
            MAX(contact) AS contact,
            MAX(discord_id) AS discord_id,
            COUNT(*) AS orders_count,
            COALESCE(SUM(amount_rub), 0) AS total_rub
        FROM donation_orders
        WHERE status = 'confirmed'
          AND datetime(created_at) >= datetime(?)
          AND datetime(created_at) <= datetime(?)
        GROUP BY donor_key
        ORDER BY total_rub DESC
        LIMIT 20
        """,
        (start, end),
    )
    top_donors = [dict(r) for r in cursor.fetchall()]

    cursor.execute(
        """
        SELECT date(created_at) AS day,
               COUNT(*) AS orders_count,
               COALESCE(SUM(amount_rub), 0) AS total_rub
        FROM donation_orders
        WHERE status = 'confirmed'
          AND datetime(created_at) >= datetime(?)
          AND datetime(created_at) <= datetime(?)
        GROUP BY date(created_at)
        ORDER BY day ASC
        """,
        (start, end),
    )
    daily = [dict(r) for r in cursor.fetchall()]

    cursor.execute(
        """
        SELECT
            SUM(CASE WHEN receipt_pdf_url IS NOT NULL AND receipt_pdf_url != '' THEN 1 ELSE 0 END) AS issued,
            SUM(CASE WHEN receipt_status = 'error' THEN 1 ELSE 0 END) AS errors,
            SUM(CASE
                WHEN (receipt_pdf_url IS NULL OR receipt_pdf_url = '')
                     AND COALESCE(receipt_status, '') != 'error'
                THEN 1 ELSE 0 END) AS missing
        FROM donation_orders
        WHERE status = 'confirmed'
          AND datetime(created_at) >= datetime(?)
          AND datetime(created_at) <= datetime(?)
        """,
        (start, end),
    )
    receipts = dict(cursor.fetchone() or {})

    conn.close()
    return {
        "date_from": date_from,
        "date_to": date_to,
        "orders_count": int(totals.get("orders_count") or 0),
        "total_rub": int(totals.get("total_rub") or 0),
        "unique_donors": int(totals.get("unique_donors") or 0),
        "by_product": by_product,
        "by_item": by_item,
        "top_donors": top_donors,
        "daily": daily,
        "receipts": {
            "issued": int(receipts.get("issued") or 0),
            "errors": int(receipts.get("errors") or 0),
            "missing": int(receipts.get("missing") or 0),
        },
    }


def ensure_donation_discounts_table():
    """Идемпотентная миграция — таблица могла появиться после старого init_social_db."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donation_discounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            percent INTEGER NOT NULL,
            scope TEXT NOT NULL DEFAULT 'all',
            target_id INTEGER,
            badge_text TEXT,
            beneficiary_player_id TEXT,
            beneficiary_discord_id TEXT,
            starts_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ends_at TIMESTAMP NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cols = _table_columns(cursor, "donation_discounts")
    if "beneficiary_player_id" not in cols:
        cursor.execute("ALTER TABLE donation_discounts ADD COLUMN beneficiary_player_id TEXT")
    if "beneficiary_discord_id" not in cols:
        cursor.execute("ALTER TABLE donation_discounts ADD COLUMN beneficiary_discord_id TEXT")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_donation_discounts_active
        ON donation_discounts(active, starts_at, ends_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_donation_discounts_beneficiary
        ON donation_discounts(beneficiary_player_id, active)
    """)
    conn.commit()
    conn.close()


def _parse_discount_dt(value) -> Optional[datetime.datetime]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _is_discount_currently_active(row: dict, now: Optional[datetime.datetime] = None) -> bool:
    if not int(row.get("active") or 0):
        return False
    now = now or datetime.datetime.now()
    start = _parse_discount_dt(row.get("starts_at")) or datetime.datetime.min
    end = _parse_discount_dt(row.get("ends_at"))
    if end is None:
        return False
    # Допуск на сдвиг TZ (UTC vs MSK): старт «в будущем» до 14ч всё ещё считаем активным,
    # если окончание ещё не наступило.
    if start > now:
        skew = start - now
        if skew <= datetime.timedelta(hours=14) and now < end:
            return True
        return False
    return now < end


def create_donation_discount(
    *,
    title: str,
    percent: int,
    scope: str = "all",
    target_id: int | None = None,
    badge_text: str | None = None,
    beneficiary_player_id: str | None = None,
    beneficiary_discord_id: str | None = None,
    starts_at: str | None = None,
    ends_at: str,
    created_by: str | None = None,
) -> dict:
    ensure_donation_discounts_table()
    now_dt = datetime.datetime.now() - datetime.timedelta(seconds=30)
    now = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    start_val = starts_at or now
    bp = (beneficiary_player_id or "").strip() or None
    bd = (beneficiary_discord_id or "").strip() or None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO donation_discounts (
            title, percent, scope, target_id, badge_text,
            beneficiary_player_id, beneficiary_discord_id,
            starts_at, ends_at, active, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (
            title,
            int(percent),
            scope,
            target_id,
            badge_text,
            bp,
            bd,
            start_val,
            ends_at,
            created_by,
        ),
    )
    conn.commit()
    did = cursor.lastrowid
    cursor.execute("SELECT * FROM donation_discounts WHERE id = ?", (did,))
    row = dict(cursor.fetchone())
    conn.close()
    return row


def list_donation_discounts(*, include_inactive: bool = True, limit: int = 100) -> list[dict]:
    ensure_donation_discounts_table()
    conn = get_db()
    cursor = conn.cursor()
    limit = min(max(int(limit), 1), 200)
    cursor.execute(
        """
        SELECT * FROM donation_discounts
        ORDER BY active DESC, ends_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    if include_inactive:
        return rows
    now = datetime.datetime.now()
    active = [r for r in rows if _is_discount_currently_active(r, now)]
    active.sort(key=lambda r: (-int(r.get("percent") or 0), str(r.get("ends_at") or "")))
    return active[:limit]


def _discount_is_personal(row: dict) -> bool:
    return bool((row.get("beneficiary_player_id") or "").strip() or (row.get("beneficiary_discord_id") or "").strip())


def _discount_belongs_to_user(row: dict, player_id: str | None, discord_id: str | None) -> bool:
    bp = (row.get("beneficiary_player_id") or "").strip()
    bd = (row.get("beneficiary_discord_id") or "").strip()
    if not bp and not bd:
        return True
    if player_id and bp and bp == str(player_id):
        return True
    if discord_id and bd and str(bd) == str(discord_id):
        return True
    return False


def get_active_donation_discounts(
    *,
    for_player_id: str | None = None,
    for_discord_id: str | None = None,
    public_only: bool = False,
) -> list[dict]:
    """Активные скидки: публичные и/или личные для указанного игрока."""
    rows = list_donation_discounts(include_inactive=False, limit=100)
    out = []
    for r in rows:
        personal = _discount_is_personal(r)
        if public_only and personal:
            continue
        if personal and not _discount_belongs_to_user(r, for_player_id, for_discord_id):
            continue
        # Личные чужим не отдаём; без for_* — только публичные
        if personal and not for_player_id and not for_discord_id:
            continue
        out.append(r)
    return out[:50]


def get_donation_discount(discount_id: int) -> Optional[Dict]:
    ensure_donation_discounts_table()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donation_discounts WHERE id = ?", (int(discount_id),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def deactivate_donation_discount(discount_id: int) -> bool:
    ensure_donation_discounts_table()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE donation_discounts SET active = 0 WHERE id = ?",
        (int(discount_id),),
    )
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def delete_donation_discount(discount_id: int) -> bool:
    ensure_donation_discounts_table()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM donation_discounts WHERE id = ?", (int(discount_id),))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok


def create_sponsorship(
    *,
    order_transaction_id: str,
    tier_id: int,
    tier_name: str,
    amount_rub: int,
    days: int = 30,
    player_id: str | None = None,
    discord_id: str | None = None,
    game_user_uuid: str | None = None,
    contact: str | None = None,
    coins_granted: int = 0,
    notes: str | None = None,
) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sponsorships WHERE order_transaction_id = ?", (order_transaction_id,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("SELECT * FROM sponsorships WHERE id = ?", (existing["id"],))
        row = dict(cursor.fetchone())
        conn.close()
        return row
    cursor.execute(
        """
        INSERT INTO sponsorships (
            order_transaction_id, player_id, discord_id, game_user_uuid, contact,
            tier_id, tier_name, amount_rub, coins_granted, ends_at, notes
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, datetime('now', ?), ?
        )
        """,
        (
            order_transaction_id,
            player_id,
            discord_id,
            game_user_uuid,
            contact,
            int(tier_id),
            tier_name,
            int(amount_rub),
            int(coins_granted or 0),
            f"+{int(days)} days",
            notes,
        ),
    )
    conn.commit()
    sid = cursor.lastrowid
    cursor.execute("SELECT * FROM sponsorships WHERE id = ?", (sid,))
    row = dict(cursor.fetchone())
    conn.close()
    return row


def get_sponsorship_by_order(order_transaction_id: str) -> dict | None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sponsorships WHERE order_transaction_id = ?",
        (order_transaction_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


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


def delete_sessions_for_discord_id(discord_id: str) -> int:
    """Удаляет все сессии пользователя по discord_id. Возвращает число удалённых."""
    if not discord_id:
        return 0
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT session_token, user_data FROM sessions")
    to_delete = []
    for row in cursor.fetchall():
        try:
            data = json.loads(row["user_data"] or "{}")
        except Exception:
            continue
        if str(data.get("discord_id") or "") == str(discord_id):
            to_delete.append(row["session_token"])
    for token in to_delete:
        cursor.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
    conn.commit()
    conn.close()
    return len(to_delete)


def get_active_site_ban(discord_id: str) -> dict | None:
    if not discord_id:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM site_bans
        WHERE discord_id = ? AND active = 1
          AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ORDER BY created_at DESC
        LIMIT 1
    """, (str(discord_id),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_site_ban(
    discord_id: str,
    player_id: str | None,
    reason: str,
    banned_by_discord_id: str | None,
    banned_by_username: str | None,
    expires_at: str | None = None,
) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE site_bans SET active = 0, lifted_at = CURRENT_TIMESTAMP, lifted_by = ?
        WHERE discord_id = ? AND active = 1
    """, (banned_by_username or "system", str(discord_id)))
    cursor.execute("""
        INSERT INTO site_bans
            (discord_id, player_id, reason, banned_by_discord_id, banned_by_username, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(discord_id),
        player_id,
        reason.strip(),
        banned_by_discord_id,
        banned_by_username,
        expires_at,
    ))
    ban_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ban_id


def lift_site_ban(discord_id: str, lifted_by: str | None = None) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE site_bans
        SET active = 0, lifted_at = CURRENT_TIMESTAMP, lifted_by = ?
        WHERE discord_id = ? AND active = 1
    """, (lifted_by or "admin", str(discord_id)))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def lift_site_ban_by_id(ban_id: int, lifted_by: str | None = None) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE site_bans
        SET active = 0, lifted_at = CURRENT_TIMESTAMP, lifted_by = ?
        WHERE id = ? AND active = 1
    """, (lifted_by or "admin", ban_id))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def list_site_bans(active_only: bool = True, limit: int = 50, offset: int = 0) -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("""
            SELECT * FROM site_bans
            WHERE active = 1
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    else:
        cursor.execute("""
            SELECT * FROM site_bans
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def cleanup_expired_sessions(max_age_days: int = 30):
    """Удаляет сессии старше указанного количества дней."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE created_at < datetime('now', '-' || ? || ' days')", (max_age_days,))
    conn.commit()
    conn.close()


# ---------- Компенсация за падение сервера ----------

def create_compensation_giveaway(amount: int, duration_minutes: int, created_by: str) -> Dict:
    ends_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration_minutes)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO compensation_giveaways (amount, ends_at, created_by) VALUES (?, ?, ?)",
        (amount, ends_at.replace(microsecond=0).isoformat(), created_by),
    )
    giveaway_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM compensation_giveaways WHERE id = ?", (giveaway_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row)


def get_compensation_giveaway_by_id(giveaway_id: int) -> Optional[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM compensation_giveaways WHERE id = ?", (giveaway_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_compensation_giveaway() -> Optional[Dict]:
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM compensation_giveaways
        WHERE ends_at > ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (now,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def has_compensation_claim(giveaway_id: int, user_uuid: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM compensation_claims WHERE giveaway_id = ? AND user_uuid = ? LIMIT 1",
        (giveaway_id, user_uuid),
    )
    found = cursor.fetchone() is not None
    conn.close()
    return found


def try_record_compensation_claim(giveaway_id: int, user_uuid: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO compensation_claims (giveaway_id, user_uuid) VALUES (?, ?)",
            (giveaway_id, user_uuid),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


def revoke_compensation_claim(giveaway_id: int, user_uuid: str) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM compensation_claims WHERE giveaway_id = ? AND user_uuid = ?",
        (giveaway_id, user_uuid),
    )
    conn.commit()
    conn.close()


def count_compensation_claims(giveaway_id: int) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM compensation_claims WHERE giveaway_id = ?",
        (giveaway_id,),
    )
    count = int(cursor.fetchone()[0] or 0)
    conn.close()
    return count


def get_compensation_summary() -> Dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM compensation_giveaways")
    total_giveaways = int(cursor.fetchone()[0] or 0)
    cursor.execute("SELECT COUNT(*) FROM compensation_claims")
    total_claims = int(cursor.fetchone()[0] or 0)
    cursor.execute("SELECT COUNT(DISTINCT user_uuid) FROM compensation_claims")
    unique_players = int(cursor.fetchone()[0] or 0)
    cursor.execute("""
        SELECT COALESCE(SUM(g.amount * sub.cnt), 0)
        FROM compensation_giveaways g
        JOIN (
            SELECT giveaway_id, COUNT(*) AS cnt
            FROM compensation_claims
            GROUP BY giveaway_id
        ) sub ON sub.giveaway_id = g.id
    """)
    total_coins = int(cursor.fetchone()[0] or 0)
    conn.close()
    return {
        "total_giveaways": total_giveaways,
        "total_claims": total_claims,
        "unique_players": unique_players,
        "total_coins_distributed": total_coins,
    }


def get_compensation_history(limit: int = 100) -> List[Dict]:
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            g.id,
            g.amount,
            g.ends_at,
            g.created_by,
            g.created_at,
            COUNT(c.user_uuid) AS claims_count
        FROM compensation_giveaways g
        LEFT JOIN compensation_claims c ON c.giveaway_id = g.id
        GROUP BY g.id
        ORDER BY g.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for row in rows:
        claims = int(row.get("claims_count") or 0)
        amount = int(row.get("amount") or 0)
        row["claims_count"] = claims
        row["coins_distributed"] = amount * claims
        row["is_active"] = (row.get("ends_at") or "") > now
    return rows
