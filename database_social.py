import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("SOCIAL_DB_PATH", "social.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(path):
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS social_users (
                player_id TEXT PRIMARY KEY,
                user_uuid TEXT NOT NULL,
                discord_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                discord_avatar TEXT,
                game_nickname TEXT NOT NULL,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS follows (
                follower_id TEXT NOT NULL,
                followee_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (follower_id, followee_id),
                FOREIGN KEY (follower_id) REFERENCES social_users(player_id),
                FOREIGN KEY (followee_id) REFERENCES social_users(player_id)
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_player_id TEXT NOT NULL,
                content TEXT NOT NULL,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_player_id) REFERENCES social_users(player_id)
            );
            CREATE TABLE IF NOT EXISTS likes (
                post_id INTEGER NOT NULL,
                player_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (post_id, player_id),
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (player_id) REFERENCES social_users(player_id)
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                author_player_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (author_player_id) REFERENCES social_users(player_id)
            );
            CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES social_users(player_id),
                FOREIGN KEY (receiver_id) REFERENCES social_users(player_id)
            );
        """)

def get_or_create_social_user(player_id, user_uuid, discord_id, discord_username, discord_avatar, game_nickname):
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM social_users WHERE player_id = ?", (player_id,))
        if cur.fetchone():
            conn.execute("UPDATE social_users SET discord_username=?, discord_avatar=?, game_nickname=? WHERE player_id=?", (discord_username, discord_avatar, game_nickname, player_id))
        else:
            conn.execute("INSERT INTO social_users (player_id, user_uuid, discord_id, discord_username, discord_avatar, game_nickname) VALUES (?,?,?,?,?,?)", (player_id, user_uuid, discord_id, discord_username, discord_avatar, game_nickname))
        conn.commit()
    return get_social_user_by_player_id(player_id)

def get_social_user_by_player_id(player_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM social_users WHERE player_id = ?", (player_id,)).fetchone()
        return dict(row) if row else None

def update_social_user(player_id, bio=None):
    with get_db() as conn:
        if bio is not None:
            conn.execute("UPDATE social_users SET bio = ? WHERE player_id = ?", (bio, player_id))
        conn.commit()

def follow_user(follower_id, followee_id):
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO follows (follower_id, followee_id) VALUES (?,?)", (follower_id, followee_id))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def unfollow_user(follower_id, followee_id):
    with get_db() as conn:
        conn.execute("DELETE FROM follows WHERE follower_id = ? AND followee_id = ?", (follower_id, followee_id))
        conn.commit()
    return True

def is_following(follower_id, followee_id):
    with get_db() as conn:
        return conn.execute("SELECT 1 FROM follows WHERE follower_id = ? AND followee_id = ?", (follower_id, followee_id)).fetchone() is not None

def get_follow_counts(player_id):
    with get_db() as conn:
        following = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (player_id,)).fetchone()[0]
        followers = conn.execute("SELECT COUNT(*) FROM follows WHERE followee_id = ?", (player_id,)).fetchone()[0]
    return {"following": following, "followers": followers}

def create_post(author_id, content, image_url=None):
    with get_db() as conn:
        cur = conn.execute("INSERT INTO posts (author_player_id, content, image_url) VALUES (?,?,?) RETURNING id", (author_id, content, image_url))
        post_id = cur.fetchone()[0]
        conn.commit()
    return post_id

def delete_post(post_id, player_id):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM posts WHERE id = ? AND author_player_id = ?", (post_id, player_id))
        conn.commit()
        return cur.rowcount > 0

def get_feed_posts(player_id, limit=20, offset=0):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.id, p.author_player_id, su.game_nickname, su.discord_username, su.discord_avatar,
                   p.content, p.image_url, p.created_at,
                   (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                   (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
                   EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND player_id = ?) as liked_by_me
            FROM posts p
            JOIN social_users su ON p.author_player_id = su.player_id
            WHERE p.author_player_id = ? OR p.author_player_id IN (SELECT followee_id FROM follows WHERE follower_id = ?)
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """, (player_id, player_id, player_id, limit, offset)).fetchall()
    return [dict(r) for r in rows]

def get_user_posts(player_id, limit=20, offset=0):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.id, p.author_player_id, su.game_nickname, su.discord_username, su.discord_avatar,
                   p.content, p.image_url, p.created_at,
                   (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                   (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count
            FROM posts p
            JOIN social_users su ON p.author_player_id = su.player_id
            WHERE p.author_player_id = ?
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """, (player_id, limit, offset)).fetchall()
    return [dict(r) for r in rows]

def toggle_like(post_id, player_id):
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM likes WHERE post_id = ? AND player_id = ?", (post_id, player_id)).fetchone():
            conn.execute("DELETE FROM likes WHERE post_id = ? AND player_id = ?", (post_id, player_id))
            action = "unliked"
        else:
            conn.execute("INSERT INTO likes (post_id, player_id) VALUES (?,?)", (post_id, player_id))
            action = "liked"
        conn.commit()
    return action

def get_like_count(post_id):
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,)).fetchone()[0]

def add_comment(post_id, author_id, content):
    with get_db() as conn:
        cur = conn.execute("INSERT INTO comments (post_id, author_player_id, content) VALUES (?,?,?) RETURNING id", (post_id, author_id, content))
        comment_id = cur.fetchone()[0]
        conn.commit()
    return comment_id

def delete_comment(comment_id, player_id):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM comments WHERE id = ? AND author_player_id = ?", (comment_id, player_id))
        conn.commit()
        return cur.rowcount > 0

def get_comments(post_id):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT c.id, c.post_id, c.author_player_id, su.game_nickname, su.discord_avatar, c.content, c.created_at
            FROM comments c JOIN social_users su ON c.author_player_id = su.player_id
            WHERE c.post_id = ? ORDER BY c.created_at
        """, (post_id,)).fetchall()
    return [dict(r) for r in rows]

def search_social_users(query, limit=20):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT player_id, game_nickname, discord_username, discord_avatar
            FROM social_users
            WHERE game_nickname LIKE ? OR discord_username LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit)).fetchall()
    return [dict(r) for r in rows]

def get_conversations(player_id):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT other_id, su.game_nickname, su.discord_avatar,
                   (SELECT COUNT(*) FROM private_messages WHERE receiver_id = ? AND sender_id = other_id AND is_read = 0) as unread
            FROM (
                SELECT DISTINCT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END as other_id
                FROM private_messages WHERE sender_id = ? OR receiver_id = ?
            ) conv
            JOIN social_users su ON conv.other_id = su.player_id
        """, (player_id, player_id, player_id, player_id)).fetchall()
    return [dict(r) for r in rows]

def get_private_messages(user1, user2):
    with get_db() as conn:
        conn.execute("UPDATE private_messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = ?", (user2, user1))
        conn.commit()
        rows = conn.execute("""
            SELECT id, sender_id, receiver_id, message, is_read, created_at
            FROM private_messages
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY created_at
        """, (user1, user2, user2, user1)).fetchall()
    return [dict(r) for r in rows]

def send_private_message(sender_id, receiver_id, message):
    with get_db() as conn:
        conn.execute("INSERT INTO private_messages (sender_id, receiver_id, message) VALUES (?,?,?)", (sender_id, receiver_id, message))
        conn.commit()