from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
from app.dependencies import get_current_admin, get_current_staff
from app.services.admin import get_site_statistics, list_admins, grant_admin, grant_moderator, revoke_admin, find_user_for_admin
from app.services.bans import get_all_bans, lift_ban
from app.services.appeals import list_appeals, review_appeal
from app.services.avatars import resolve_avatar_url
from app.services.social import get_feed_posts
from app.services.admin_rating import list_admin_help_ratings, delete_admin_help_rating, get_admin_rating_leaderboard
import database_social as social_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


class GrantAdminRequest(BaseModel):
    discord_username: str
    role: str = "admin"


class ReviewAppealRequest(BaseModel):
    status: str
    admin_response: str = ""


@router.get("/admin-ratings/leaders")
async def admin_rating_leaders(request: Request):
    await get_current_admin(request)
    return await get_admin_rating_leaderboard()


@router.get("/admin-ratings/{user_uuid}")
async def admin_rating_details(request: Request, user_uuid: str):
    await get_current_admin(request)
    try:
        data = await list_admin_help_ratings(user_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректный UUID администратора")
    if data is None:
        raise HTTPException(status_code=404, detail="Администратор не найден")
    return data


@router.delete("/admin-ratings/{rating_id}")
async def admin_delete_rating(rating_id: int, request: Request):
    admin = await get_current_admin(request)
    result = await delete_admin_help_rating(rating_id)
    if not result:
        raise HTTPException(status_code=404, detail="Оценка не найдена")
    social_db.log_rating_removal(
        result["id"],
        result["admin_uuid"],
        result.get("player_uuid"),
        result["stars"],
        admin.get("username", "admin"),
    )
    return {"success": True, **result}


@router.get("/stats")
async def admin_stats(request: Request):
    await get_current_admin(request)
    return await get_site_statistics()


@router.get("/users")
async def admin_users(request: Request, q: str = "", limit: int = 50, offset: int = 0):
    await get_current_admin(request)
    users = social_db.list_all_social_users(q, limit, offset)
    return {
        "total": social_db.count_social_users(),
        "users": [
            {
                **u,
                "avatar": resolve_avatar_url(u),
                "is_admin": social_db.is_site_admin(u.get("discord_id", "")),
                "is_moderator": social_db.is_site_moderator(u.get("discord_id", "")),
                "staff_role": social_db.get_site_staff_role(u.get("discord_id", "")),
            }
            for u in users
        ],
    }


@router.get("/posts")
async def admin_posts(request: Request, limit: int = 30, offset: int = 0):
    await get_current_admin(request)
    posts = get_feed_posts(None, limit, offset)
    from app.routers.social import profile_avatar
    return [
        {
            "id": p["id"],
            "author_player_id": p["author_player_id"],
            "author_nickname": p.get("game_nickname"),
            "author_discord": p.get("discord_username"),
            "author_avatar": profile_avatar(p),
            "content": p["content"],
            "image_url": p.get("image_url"),
            "category": p.get("category") or "forum",
            "category_label": social_db.POST_CATEGORIES.get(p.get("category") or "forum", "Форум"),
            "topic": p.get("topic"),
            "topic_label": social_db.POST_TOPICS.get(p.get("topic"), "") if p.get("topic") else "",
            "title": p.get("title") or "",
            "like_count": p.get("like_count", 0),
            "comment_count": p.get("comment_count", 0),
            "created_at": p["created_at"],
        }
        for p in posts
    ]


@router.get("/admins")
async def admin_list(request: Request):
    await get_current_admin(request)
    return list_admins()


@router.post("/admins")
async def admin_grant(req: GrantAdminRequest, request: Request):
    admin = await get_current_admin(request)
    username = req.discord_username.strip().lstrip("@")
    if not username:
        raise HTTPException(status_code=400, detail="Укажите Discord-ник")
    user = find_user_for_admin(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден. Он должен войти на сайт хотя бы раз.")
    role = req.role if req.role in ("admin", "moderator") else "admin"
    if role == "admin":
        grant_admin(user["discord_id"], user.get("discord_username") or username, admin.get("username", ""))
    else:
        grant_moderator(user["discord_id"], user.get("discord_username") or username, admin.get("username", ""))
    return {"success": True, "discord_id": user["discord_id"], "discord_username": user.get("discord_username"), "role": role}


@router.delete("/admins/{discord_id}")
async def admin_revoke(discord_id: str, request: Request):
    admin = await get_current_admin(request)
    if discord_id == admin.get("discord_id"):
        raise HTTPException(status_code=400, detail="Нельзя снять админку с самого себя")
    if not revoke_admin(discord_id):
        raise HTTPException(status_code=404, detail="Администратор не найден")
    return {"success": True}


@router.delete("/posts/{post_id}")
async def admin_delete_post(post_id: int, request: Request):
    await get_current_admin(request)
    if not social_db.admin_delete_post(post_id):
        raise HTTPException(status_code=404, detail="Пост не найден")
    return {"success": True}


@router.get("/bans")
async def admin_all_bans(request: Request, limit: int = 50, offset: int = 0):
    await get_current_admin(request)
    return await get_all_bans(limit, offset)


@router.get("/appeals")
async def admin_appeals(request: Request, status: str = Query("", max_length=20), limit: int = 50, offset: int = 0):
    await get_current_staff(request)
    st = status if status in ("pending", "approved", "rejected") else None
    return list_appeals(st, limit, offset)


@router.post("/appeals/{appeal_id}/review")
async def admin_review_appeal(appeal_id: int, req: ReviewAppealRequest, request: Request):
    staff = await get_current_staff(request)
    appeal = social_db.get_ban_appeal_by_id(appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Обжалование не найдено")
    if appeal.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Обжалование уже рассмотрено")
    try:
        if req.status == "approved":
            lifted = await lift_ban(appeal["ban_id"])
            if not lifted:
                raise HTTPException(status_code=404, detail="Бан не найден в игровой БД (возможно, уже снят)")
        ok = review_appeal(appeal_id, req.status, req.admin_response, staff.get("username", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Обжалование не найдено")
    return {"success": True}
