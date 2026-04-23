import os
import shutil
import datetime
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from app.dependencies import get_current_user, get_current_player
from app.models.social import ProfileUpdate, CommentCreate
from app.services.social import (
    get_social_user_by_player_id, update_social_user, create_post, delete_post,
    toggle_like, get_like_count, add_comment, get_comments, delete_comment,
    follow_user, unfollow_user, is_following, get_follow_counts,
    get_followers, get_following, get_feed_posts, get_user_posts,
    search_social_users
)
from app.config import UPLOAD_DIR
import database_social as social_db

router = APIRouter(prefix="/api/social", tags=["social"])


@router.get("/profile/{player_id}")
async def api_get_profile(request: Request, player_id: str):
    current_user = await get_current_user(request)
    my_player_id = current_user.get('player', {}).get('player_id')

    profile = get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    counts = get_follow_counts(player_id)
    following = False
    if my_player_id:
        following = is_following(my_player_id, player_id)

    return {
        "player_id": profile["player_id"],
        "game_nickname": profile["game_nickname"],
        "discord_username": profile["discord_username"],
        "discord_avatar": profile["discord_avatar"],
        "bio": profile["bio"],
        "following_count": counts["following"],
        "followers_count": counts["followers"],
        "is_following": following,
        "created_at": profile["created_at"]
    }


@router.post("/profile/update")
async def api_update_profile(request: Request, update: ProfileUpdate):
    player = await get_current_player(request)
    update_social_user(player['player_id'], bio=update.bio)
    return {"success": True}


@router.post("/posts")
async def api_create_post(
    request: Request,
    content: str = Form(...),
    image: UploadFile | None = File(None)
):
    player = await get_current_player(request)
    image_url = None
    if image and image.filename:
        file_ext = os.path.splitext(image.filename)[1]
        filename = f"{player['player_id']}_{int(datetime.datetime.now().timestamp())}{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/{filename}"

    post_id = create_post(player['player_id'], content, image_url)
    return {"success": True, "post_id": post_id}


@router.get("/posts/feed")
async def api_feed(request: Request, limit: int = 20, offset: int = 0):
    player = await get_current_player(request)
    posts = get_feed_posts(player['player_id'], limit, offset)
    result = []
    for p in posts:
        result.append({
            "id": p["id"],
            "author_player_id": p["author_player_id"],
            "author_nickname": p["game_nickname"],
            "author_discord_username": p["discord_username"],
            "author_avatar": p["discord_avatar"],
            "content": p["content"],
            "image_url": p["image_url"],
            "like_count": p["like_count"],
            "comment_count": p["comment_count"],
            "liked_by_me": bool(p["liked_by_me"]),
            "created_at": p["created_at"]
        })
    return result


@router.get("/posts/user/{player_id}")
async def api_user_posts(request: Request, player_id: str, limit: int = 20, offset: int = 0):
    viewer_id = None
    try:
        player = await get_current_player(request)
        viewer_id = player['player_id']
    except HTTPException:
        pass

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
        result.append({
            "id": p["id"],
            "author_player_id": p["author_player_id"],
            "author_nickname": p["game_nickname"],
            "author_discord_username": p["discord_username"],
            "author_avatar": p["discord_avatar"],
            "content": p["content"],
            "image_url": p["image_url"],
            "like_count": p["like_count"],
            "comment_count": p["comment_count"],
            "liked_by_me": liked,
            "created_at": p["created_at"]
        })
    return result


@router.delete("/posts/{post_id}")
async def api_delete_post(request: Request, post_id: int):
    player = await get_current_player(request)
    success = delete_post(post_id, player['player_id'])
    if not success:
        raise HTTPException(status_code=404, detail="Пост не найден или нет прав")
    return {"success": True}


@router.post("/posts/{post_id}/like")
async def api_toggle_like(request: Request, post_id: int):
    player = await get_current_player(request)
    action = toggle_like(post_id, player['player_id'])
    like_count = get_like_count(post_id)
    return {"action": action, "like_count": like_count}


@router.post("/posts/{post_id}/comments")
async def api_add_comment(request: Request, post_id: int, comment: CommentCreate):
    player = await get_current_player(request)
    comment_id = add_comment(post_id, player['player_id'], comment.content)
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
            "author_nickname": c["game_nickname"],
            "author_avatar": c["discord_avatar"],
            "content": c["content"],
            "created_at": c["created_at"]
        })
    return result


@router.delete("/comments/{comment_id}")
async def api_delete_comment(request: Request, comment_id: int):
    player = await get_current_player(request)
    success = delete_comment(comment_id, player['player_id'])
    if not success:
        raise HTTPException(status_code=404, detail="Комментарий не найден или нет прав")
    return {"success": True}


@router.post("/follow/{target_player_id}")
async def api_follow(request: Request, target_player_id: str):
    player = await get_current_player(request)
    if player['player_id'] == target_player_id:
        raise HTTPException(status_code=400, detail="Нельзя подписаться на себя")
    success = follow_user(player['player_id'], target_player_id)
    if not success:
        raise HTTPException(status_code=400, detail="Уже подписаны или ошибка")
    return {"success": True, "following": True}


@router.delete("/follow/{target_player_id}")
async def api_unfollow(request: Request, target_player_id: str):
    player = await get_current_player(request)
    success = unfollow_user(player['player_id'], target_player_id)
    return {"success": success}


@router.get("/followers/{player_id}")
async def api_get_followers(player_id: str, limit: int = 20):
    followers = get_followers(player_id, limit)
    return followers


@router.get("/following/{player_id}")
async def api_get_following(player_id: str, limit: int = 20):
    following = get_following(player_id, limit)
    return following


@router.get("/search")
async def api_social_search(q: str, limit: int = 20):
    if len(q) < 2:
        return []
    try:
        from app.services.bank import search_all_players
        results = await search_all_players(q, limit)
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []