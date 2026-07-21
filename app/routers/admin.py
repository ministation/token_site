from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
from app.dependencies import get_current_admin, get_current_staff
from app.services.admin import (
    get_site_statistics, list_admins, grant_admin, grant_moderator,
    grant_content_maker, revoke_admin, revoke_content_maker,
    grant_time_keeper, revoke_time_keeper, find_user_for_admin,
)
from app.services.bans import (
    get_all_bans, lift_ban, unban_ban, create_server_ban, create_role_ban,
    search_players, list_job_roles,
)
from app.services.player_admin import get_full_player_dossier
from app.services.appeals import list_appeals, review_appeal
from app.services.avatars import resolve_avatar_url
from app.services.social import get_feed_posts
from app.services.admin_rating import list_admin_help_ratings, delete_admin_help_rating, get_admin_rating_leaderboard
from app.services.compensation import get_admin_compensation_status, start_compensation_giveaway
import database_social as social_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


class GrantAdminRequest(BaseModel):
    discord_username: str
    role: str = "admin"


class ReviewAppealRequest(BaseModel):
    status: str
    admin_response: str = ""


class ReviewTicketRequest(BaseModel):
    status: str
    admin_response: str = ""


class CreateServerBanRequest(BaseModel):
    player: str
    reason: str
    length_minutes: int = 0
    use_last_ip: bool = False


class CreateRoleBanRequest(BaseModel):
    player: str
    role_id: str | None = None
    role_ids: list[str] | None = None
    reason: str
    length_minutes: int = 0


class StartCompensationRequest(BaseModel):
    amount: int
    duration_minutes: int


def _admin_game_uuid(admin: dict) -> str | None:
    player = admin.get("player") or {}
    return player.get("user_uuid")


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


@router.get("/compensation")
async def admin_compensation_status(request: Request):
    await get_current_admin(request)
    return get_admin_compensation_status()


@router.post("/compensation")
async def admin_start_compensation(req: StartCompensationRequest, request: Request):
    admin = await get_current_admin(request)
    try:
        data = start_compensation_giveaway(
            req.amount,
            req.duration_minutes,
            admin.get("username", "admin"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, **data}


@router.get("/users")
async def admin_users(request: Request, q: str = "", limit: int = 50, offset: int = 0):
    await get_current_admin(request)
    from app.services.presence import status_from_last_seen
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
                "presence": status_from_last_seen(u.get("last_seen_at")),
            }
            for u in users
        ],
    }


@router.get("/posts")
async def admin_posts(request: Request, limit: int = 30, offset: int = 0):
    await get_current_admin(request)
    posts = get_feed_posts(None, limit, offset)
    from app.routers.social import profile_avatar
    from app.services.presence import statuses_for
    presence_map = statuses_for([p.get("author_player_id") for p in posts])
    return [
        {
            "id": p["id"],
            "author_player_id": p["author_player_id"],
            "author_nickname": p.get("game_nickname"),
            "author_discord": p.get("discord_username"),
            "author_avatar": profile_avatar(p),
            "author_presence": presence_map.get(p.get("author_player_id"), "offline"),
            "title": p.get("title") or "",
            "content": p["content"],
            "category": p.get("category"),
            "category_label": social_db.POST_CATEGORIES.get(p.get("category") or "forum", p.get("category")),
            "topic_label": social_db.POST_TOPICS.get(p.get("topic"), "") if p.get("topic") else "",
            "like_count": p["like_count"],
            "comment_count": p["comment_count"],
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
    role = req.role if req.role in ("admin", "moderator", "content_maker", "time_keeper") else "admin"
    if role == "admin":
        grant_admin(user["discord_id"], user.get("discord_username") or username, admin.get("username", ""))
    elif role == "moderator":
        grant_moderator(user["discord_id"], user.get("discord_username") or username, admin.get("username", ""))
    elif role == "content_maker":
        grant_content_maker(user["discord_id"], user.get("discord_username") or username, admin.get("username", "admin"))
    else:
        grant_time_keeper(user["discord_id"], user.get("discord_username") or username, admin.get("username", "admin"))
    return {"success": True, "discord_id": user["discord_id"], "discord_username": user.get("discord_username"), "role": role}


@router.delete("/admins/{discord_id}")
async def admin_revoke(discord_id: str, request: Request):
    admin = await get_current_admin(request)
    if discord_id == admin.get("discord_id"):
        raise HTTPException(status_code=400, detail="Нельзя снять админку с самого себя")
    if not revoke_admin(discord_id):
        raise HTTPException(status_code=404, detail="Администратор не найден")
    return {"success": True}


@router.post("/content-makers")
async def content_maker_grant(req: GrantAdminRequest, request: Request):
    admin = await get_current_admin(request)
    username = req.discord_username.strip().lstrip("@")
    if not username:
        raise HTTPException(status_code=400, detail="Укажите Discord-ник")
    user = find_user_for_admin(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден. Он должен войти на сайт хотя бы раз.")
    grant_content_maker(user["discord_id"], user.get("discord_username") or username, admin.get("username", "admin"))
    return {"success": True, "discord_id": user["discord_id"], "discord_username": user.get("discord_username")}


@router.delete("/content-makers/{discord_id}")
async def content_maker_revoke(discord_id: str, request: Request):
    await get_current_admin(request)
    if not revoke_content_maker(discord_id):
        raise HTTPException(status_code=404, detail="Контент-мейкер не найден")
    return {"success": True}


@router.post("/time-keepers")
async def time_keeper_grant(req: GrantAdminRequest, request: Request):
    admin = await get_current_admin(request)
    username = req.discord_username.strip().lstrip("@")
    if not username:
        raise HTTPException(status_code=400, detail="Укажите Discord-ник")
    user = find_user_for_admin(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден. Он должен войти на сайт хотя бы раз.")
    grant_time_keeper(user["discord_id"], user.get("discord_username") or username, admin.get("username", "admin"))
    return {"success": True, "discord_id": user["discord_id"], "discord_username": user.get("discord_username")}


@router.delete("/time-keepers/{discord_id}")
async def time_keeper_revoke(discord_id: str, request: Request):
    await get_current_admin(request)
    if not revoke_time_keeper(discord_id):
        raise HTTPException(status_code=404, detail="Хранитель времени не найден")
    return {"success": True}


@router.get("/badges")
async def staff_badges_list(request: Request):
    await get_current_admin(request)
    return {
        "content_makers": social_db.list_content_makers(),
        "time_keepers": social_db.list_time_keepers(),
    }


@router.delete("/posts/{post_id}")
async def admin_delete_post(post_id: int, request: Request):
    await get_current_admin(request)
    if not social_db.admin_delete_post(post_id):
        raise HTTPException(status_code=404, detail="Пост не найден")
    return {"success": True}


@router.get("/bans")
async def admin_all_bans(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    ban_type: int | None = None,
    status: str = "all",
    player: str = Query(""),
    q: str = Query(""),
):
    await get_current_staff(request)
    if ban_type is not None and ban_type not in (0, 1):
        raise HTTPException(status_code=400, detail="Некорректный тип бана")
    if status not in ("all", "active", "expired"):
        raise HTTPException(status_code=400, detail="Некорректный фильтр статуса")
    player_uuid = player.strip() or None
    return await get_all_bans(
        limit=limit,
        offset=offset,
        ban_type=ban_type,
        status=status,
        player_uuid=player_uuid,
        search=q.strip() or None,
    )


@router.post("/bans/server")
async def admin_create_server_ban(req: CreateServerBanRequest, request: Request):
    admin = await get_current_staff(request)
    try:
        result = await create_server_ban(
            _admin_game_uuid(admin),
            req.player,
            req.reason,
            req.length_minutes,
            req.use_last_ip,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, **result}


@router.post("/bans/role")
async def admin_create_role_ban(req: CreateRoleBanRequest, request: Request):
    admin = await get_current_staff(request)
    role_ids = [r.strip() for r in (req.role_ids or []) if r and r.strip()]
    if not role_ids and req.role_id:
        role_ids = [req.role_id.strip()]
    if not role_ids:
        raise HTTPException(status_code=400, detail="Выберите хотя бы одну должность")
    try:
        result = await create_role_ban(
            _admin_game_uuid(admin),
            req.player,
            role_ids,
            req.reason,
            req.length_minutes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не удалось выдать джоббан: {e}")
    return {"success": True, **result}


@router.post("/bans/{ban_id}/unban")
async def admin_unban(ban_id: int, request: Request):
    admin = await get_current_staff(request)
    ok = await unban_ban(ban_id, _admin_game_uuid(admin))
    if not ok:
        raise HTTPException(status_code=404, detail="Бан не найден")
    return {"success": True, "ban_id": ban_id}


@router.get("/game/players/search")
async def admin_search_players(request: Request, q: str = Query("", min_length=2)):
    await get_current_staff(request)
    return await search_players(q)


@router.get("/game/players/{user_uuid}")
async def admin_player_profile(request: Request, user_uuid: str):
    await get_current_staff(request)
    profile = await get_full_player_dossier(user_uuid)
    if not profile:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    return profile


@router.get("/game/jobs")
async def admin_job_list(request: Request):
    await get_current_staff(request)
    return list_job_roles()


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
            lifted = await lift_ban(appeal["ban_id"], _admin_game_uuid(staff))
            if not lifted:
                raise HTTPException(status_code=404, detail="Бан не найден в игровой БД (возможно, уже снят)")
        ok = review_appeal(appeal_id, req.status, req.admin_response, staff.get("username", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Обжалование не найдено")
    return {"success": True}


@router.get("/support-tickets")
async def admin_support_tickets(
    request: Request,
    status: str = Query("", max_length=20),
    limit: int = 50,
    offset: int = 0,
):
    await get_current_staff(request)
    from app.services import support as support_svc
    return support_svc.list_tickets(status, limit, offset)


@router.post("/support-tickets/{ticket_id}/review")
async def admin_review_support_ticket(ticket_id: int, req: ReviewTicketRequest, request: Request):
    staff = await get_current_staff(request)
    from app.services import support as support_svc
    try:
        ok = support_svc.reply_ticket(
            ticket_id, req.status, req.admin_response, staff.get("username", "")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    return {"success": True}
