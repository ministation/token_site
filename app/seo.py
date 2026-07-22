"""Open Graph / Twitter Card meta for link previews in social apps."""

from __future__ import annotations

from urllib.parse import urljoin

from fastapi import Request

from app.config import SITE_PUBLIC_URL

SITE_NAME = "Мини-станция"
DEFAULT_DESCRIPTION = (
    "Некоммерческий сервер Space Station 14: роли, баталии, "
    "сообщество, монетки и донат."
)
DONATE_DESCRIPTION = (
    "Поддержи Мини-станцию: подписки с Discord-ролями, цветом ника, "
    "пропуском очереди и пакетами монеток."
)


def absolute_url(path: str) -> str:
    base = SITE_PUBLIC_URL.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def social_meta(
    request: Request | None = None,
    *,
    title: str = SITE_NAME,
    description: str = DEFAULT_DESCRIPTION,
    path: str = "/",
    image: str = "/static/og-default.png",
    image_alt: str | None = None,
) -> dict:
    """Контекст для partials/social_meta.html."""
    page_url = absolute_url(path)
    # Локальная отладка: если публичный URL не задан явно под localhost
    if request is not None and ("localhost" in SITE_PUBLIC_URL or "127.0.0.1" in SITE_PUBLIC_URL):
        page_url = str(request.base_url).rstrip("/") + (path if path.startswith("/") else f"/{path}")

    image_url = absolute_url(image) if image.startswith("/") else image
    full_title = title if title == SITE_NAME or title.startswith(SITE_NAME) else f"{title} — {SITE_NAME}"

    return {
        "og_site_name": SITE_NAME,
        "og_title": full_title,
        "og_description": description,
        "og_url": page_url,
        "og_image": image_url,
        "og_image_alt": image_alt or full_title,
        "og_locale": "ru_RU",
        "og_type": "website",
        "twitter_card": "summary_large_image",
    }


def home_social_meta(request: Request) -> dict:
    return social_meta(
        request,
        title=SITE_NAME,
        description=DEFAULT_DESCRIPTION,
        path="/",
        image="/static/og-default.png",
        image_alt="Мини-станция — Space Station 14",
    )


def donate_social_meta(request: Request) -> dict:
    return social_meta(
        request,
        title="Донат",
        description=DONATE_DESCRIPTION,
        path="/donate",
        image="/static/og-donate.png",
        image_alt="Донат — Мини-станция",
    )
