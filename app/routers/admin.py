from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
from app.dependencies import get_current_admin
from app.services.admin import get_site_statistics, list_admins, grant_admin, revoke_admin, find_user_for_admin
from app.services.bans import get_all_bans
from app.services.appeals import list_appeals, review_appeal
from app.services.avatars import resolve_avatar_url
from app.services.social import get_feed_posts
import database_social as social_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


class GrantAdminRequest(BaseModel):
    discord_username: str


class ReviewAppealRequest(BaseModel):
    status: str
    admin_response: str = ""


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
    grant_admin(user["discord_id"], user.get("discord_username") or username, admin.get("username", ""))
    return {"success": True, "discord_id": user["discord_id"], "discord_username": user.get("discord_username")}


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
    await get_current_admin(request)
    st = status if status in ("pending", "approved", "rejected") else None
    return list_appeals(st, limit, offset)


@router.post("/appeals/{appeal_id}/review")
async def admin_review_appeal(appeal_id: int, req: ReviewAppealRequest, request: Request):
    admin = await get_current_admin(request)
    try:
        ok = review_appeal(appeal_id, req.status, req.admin_response, admin.get("username", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Обжалование не найдено")
    return {"success": True}
