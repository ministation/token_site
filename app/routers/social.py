import os
import shutil
import datetime
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from app.dependencies import get_current_user, get_current_player, get_current_social_user, get_optional_social_user, get_current_admin
from app.models.social import ProfileUpdate, CommentCreate
from app.services.avatars import resolve_avatar_url, save_custom_avatar
from app.services.social import (
    get_social_user_by_player_id, update_social_user, create_post, delete_post,
    toggle_like, get_like_count, add_comment, get_comments, delete_comment,
    follow_user, unfollow_user, is_following, get_follow_counts,
    get_followers, get_following, get_feed_posts, get_user_posts,
    search_social_users
)
from app.config import UPLOAD_DIR
import database_social as social_db
from app.services.bank import get_balance_by_player_id

router = APIRouter(prefix="/api/social", tags=["social"])


def profile_avatar(row: dict) -> str:
    return resolve_avatar_url(row)


def serialize_post(p: dict, *, anonymize: bool = False) -> dict:
    category = p.get("category") or "forum"
    topic = p.get("topic")
    data = {
        "id": p["id"],
        "title": p.get("title") or "",
        "content": p["content"],
        "image_url": p.get("image_url"),
        "category": category,
        "category_label": social_db.POST_CATEGORIES.get(category, category),
        "topic": topic,
        "topic_label": social_db.POST_TOPICS.get(topic, "") if topic else "",
        "like_count": p["like_count"],
        "comment_count": p["comment_count"],
        "liked_by_me": bool(p.get("liked_by_me")),
        "created_at": p["created_at"],
    }
    if anonymize or category == "news":
        data["author_player_id"] = ""
        data["author_nickname"] = ""
        data["author_discord_username"] = ""
        data["author_discord_id"] = ""
        data["author_avatar"] = None
    else:
        data["author_player_id"] = p["author_player_id"]
        data["author_nickname"] = p["game_nickname"]
        data["author_discord_username"] = p["discord_username"]
        data["author_discord_id"] = p.get("discord_id", "")
        data["author_avatar"] = profile_avatar(p)
    return data


# ==================== ПРОФИЛЬ ====================

@router.get("/profile/{player_id}")
async def api_get_profile(request: Request, player_id: str):
    my_player_id = None
    try:
        current_user = await get_current_user(request)
        my_player_id = current_user.get('player', {}).get('player_id')
    except:
        pass

    profile = get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    avatar = profile_avatar(profile)

    counts = get_follow_counts(player_id)
    following = False
    if my_player_id:
        following = is_following(my_player_id, player_id)

    return {
        "player_id": profile["player_id"],
        "game_nickname": profile["game_nickname"],
        "discord_username": profile["discord_username"],
        "discord_id": profile.get("discord_id"),
        "discord_avatar": avatar,
        "bio": profile.get("bio", ""),
        "following_count": counts["following"],
        "followers_count": counts["followers"],
        "is_following": following,
        "is_own": my_player_id == profile["player_id"],
        "created_at": profile["created_at"]
    }


@router.post("/profile/update")
async def api_update_profile(request: Request, update: ProfileUpdate):
    player = await get_current_player(request)
    update_social_user(player['player_id'], bio=update.bio)
    return {"success": True}


# ==================== ПОСТЫ ====================

@router.get("/posts/meta")
async def api_posts_meta():
    return {
        "categories": social_db.POST_CATEGORIES,
        "topics": social_db.POST_TOPICS,
    }


@router.post("/posts")
async def api_create_post(
    request: Request,
    content: str = Form(...),
    category: str = Form("forum"),
    topic: str = Form(""),
    title: str = Form(""),
    image: UploadFile | None = File(None)
):
    user = await get_current_social_user(request)
    category = (category or "forum").strip().lower()
    if category not in social_db.VALID_CATEGORIES:
        category = "forum"
    if category == "news" and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Новости могут публиковать только администраторы")
    topic_val = (topic or "").strip().lower() or None
    if category != "discussion":
        topic_val = None
    elif topic_val and topic_val not in social_db.VALID_TOPICS:
        topic_val = "other"
    title_val = (title or "").strip() or None
    image_url = None
    if image and image.filename:
        file_ext = os.path.splitext(image.filename)[1]
        filename = f"{user['social_id']}_{int(datetime.datetime.now().timestamp())}{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/{filename}"

    post_id = create_post(
        user['social_id'], content, image_url,
        category=category, topic=topic_val, title=title_val,
    )
    return {"success": True, "post_id": post_id}


@router.get("/posts/feed")
async def api_feed(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    category: str | None = None,
    topic: str | None = None,
):
    viewer = await get_optional_social_user(request)
    viewer_id = viewer['social_id'] if viewer else None
    cat = (category or "").strip().lower() or None
    top = (topic or "").strip().lower() or None
    posts = get_feed_posts(viewer_id, limit, offset, cat, top)
    return [serialize_post(p) for p in posts]


@router.get("/posts/user/{player_id}")
async def api_user_posts(request: Request, player_id: str, limit: int = 20, offset: int = 0):
    viewer = await get_optional_social_user(request)
    viewer_id = viewer['social_id'] if viewer else None

    posts = get_user_posts(player_id, limit, offset)
    result = []
    for p in posts:
        liked = False
        if viewer_id:
            conn = social_db.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM likes WHERE post_id = ? AND player_id = ?", (p["id"], viewer_id))
            liked = cursor.fetchone() is not None
            conn.close()
        result.append(serialize_post({**p, "liked_by_me": liked}))
    return result


@router.delete("/posts/{post_id}")
async def api_delete_post(request: Request, post_id: int):
    user = await get_current_social_user(request)
    success = delete_post(post_id, user['social_id'])
    if not success and user.get("is_admin"):
        success = social_db.admin_delete_post(post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Пост не найден или нет прав")
    return {"success": True}


@router.post("/profile/avatar")
async def api_upload_avatar(request: Request, image: UploadFile = File(...)):
    user = await get_current_social_user(request)
    if not image.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")
    ext = os.path.splitext(image.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        raise HTTPException(status_code=400, detail="Допустимы PNG, JPG, WEBP, GIF")
    data = await image.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Максимум 2 МБ")
    path = save_custom_avatar(user["social_id"], user["discord_id"], data, ext)
    from app.core.sessions import get_session, set_session
    token = request.cookies.get("session_token")
    if token:
        session = get_session(token)
        if session:
            session["avatar"] = path
            set_session(token, session)
    return {"success": True, "avatar": path}


# ==================== ЛАЙКИ ====================

@router.post("/posts/{post_id}/like")
async def api_toggle_like(request: Request, post_id: int):
    user = await get_current_social_user(request)
    action = toggle_like(post_id, user['social_id'])
    like_count = get_like_count(post_id)
    return {"action": action, "like_count": like_count}


# ==================== КОММЕНТАРИИ ====================

@router.post("/posts/{post_id}/comments")
async def api_add_comment(request: Request, post_id: int, comment: CommentCreate):
    user = await get_current_social_user(request)
    comment_id = add_comment(post_id, user['social_id'], comment.content)
    return {"success": True, "comment_id": comment_id}


@router.get("/posts/{post_id}/comments")
async def api_get_comments(post_id: int):
    comments = get_comments(post_id)
    result = []
    for c in comments:
        result.append({
            "id": c["id"],
            "post_id": c["post_id"],
            "author_player_id": c["author_player_id"],
            "author_nickname": c.get("game_nickname", "Unknown"),
            "author_avatar": profile_avatar(c),
            "content": c["content"],
            "created_at": c["created_at"]
        })
    return result


@router.delete("/comments/{comment_id}")
async def api_delete_comment(request: Request, comment_id: int):
    user = await get_current_social_user(request)
    success = delete_comment(comment_id, user['social_id'])
    if not success:
        raise HTTPException(status_code=404, detail="Комментарий не найден или нет прав")
    return {"success": True}


# ==================== ПОДПИСКИ ====================

@router.post("/follow/{target_player_id}")
async def api_follow(request: Request, target_player_id: str):
    user = await get_current_social_user(request)
    if user['social_id'] == target_player_id:
        raise HTTPException(status_code=400, detail="Нельзя подписаться на себя")
    success = follow_user(user['social_id'], target_player_id)
    if not success:
        raise HTTPException(status_code=400, detail="Уже подписаны или ошибка")
    return {"success": True, "following": True}


@router.delete("/follow/{target_player_id}")
async def api_unfollow(request: Request, target_player_id: str):
    user = await get_current_social_user(request)
    success = unfollow_user(user['social_id'], target_player_id)
    return {"success": success}


@router.get("/followers/{player_id}")
async def api_get_followers(player_id: str, limit: int = 20):
    followers = get_followers(player_id, limit)
    return followers


@router.get("/following/{player_id}")
async def api_get_following(player_id: str, limit: int = 20):
    following = get_following(player_id, limit)
    return following


# ==================== ПОИСК ====================

@router.get("/search")
async def api_social_search(q: str = "", limit: int = 50):
    """Поиск только среди пользователей соцсети."""
    try:
        if len(q) >= 2:
            results = search_social_users(q, limit)
        else:
            results = search_social_users("", limit)
        
        from app.services.bank import get_balance_by_player_id
        
        enriched = []
        for r in results:
            try:
                balance = await get_balance_by_player_id(r["player_id"])
            except:
                balance = 0
            enriched.append({
                "player_id": r["player_id"],
                "game_nickname": r.get("game_nickname", "Unknown"),
                "nickname": r.get("game_nickname", "Unknown"),
                "discord_username": r.get("discord_username"),
                "discord_avatar": profile_avatar(r),
                "balance": balance,
            })
        return enriched
    except Exception as e:
        print(f"Search error: {e}")
        return []