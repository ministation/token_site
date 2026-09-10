"""Generate polished OG preview images (1200×630) for social media embeds.

Design inspired by Zen Browser: clean, modern, generous whitespace,
bold typography, warm accent colour on a calm dark background.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630

# ── palette ──────────────────────────────────────────────────────────────────
BG       = (14, 14, 20)
ACCENT   = (240, 120, 10)
WHITE    = (255, 255, 255)
GREY     = (160, 160, 172)
SS14_BLUE = (40, 103, 224)

STATIC = Path(__file__).resolve().parent.parent / "static"


# ── helpers ──────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["segoeuib.ttf" if bold else "segoeui.ttf",
             "arialbd.ttf" if bold else "arial.ttf",
             "tahoma.ttf"]
    for name in names:
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _glow(img: Image.Image, cx: int, cy: int, r: int, rgb: tuple[int, int, int]):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for s in range(r, 0, -3):
        a = int(32 * (1 - s / r))
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=(*rgb, a))
    img.alpha_composite(ov)


def _ss14_logo(size: int = 150) -> Image.Image:
    """Draw the SS14 icon (blue planet + orbital rings) in pure Pillow."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 2 - 4

    # blue sphere
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SS14_BLUE + (255,))
    # shadow gradient (bottom half darker)
    for y in range(cy, cy + r):
        frac = (y - cy) / r
        a = int(80 * frac)
        d.line([(cx - int(math.sqrt(max(r*r - (y-cy)**2, 0))), y),
                (cx + int(math.sqrt(max(r*r - (y-cy)**2, 0))), y)],
               fill=(0, 0, 0, a))

    # orbital rings
    ring_r = int(r * 0.68)
    ring_w = max(3, size // 40)
    for angle_deg in (-28, 28):
        ring_overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring_overlay)
        rd.ellipse([cx - ring_r, cy - int(ring_r * 0.28),
                     cx + ring_r, cy + int(ring_r * 0.28)],
                    outline=WHITE + (200,), width=ring_w)
        ring_overlay = ring_overlay.rotate(angle_deg, center=(cx, cy), resample=Image.BICUBIC)
        img.alpha_composite(ring_overlay)

    # white core dot
    cr = max(3, size // 20)
    d2 = ImageDraw.Draw(img)
    d2.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=WHITE + (255,))
    return img


def _coin_icon(size: int = 140) -> Image.Image:
    """Draw a stylised coin (orange circle with inner ring)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 2 - 4
    # outer circle
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT + (255,))
    # inner highlight ring
    ir = int(r * 0.72)
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], outline=(255, 200, 80, 140), width=3)
    # $ symbol
    sf = _font(int(r * 0.9), bold=True)
    sb = d.textbbox((0, 0), "$", font=sf)
    sw, sh = sb[2] - sb[0], sb[3] - sb[1]
    d.text((cx - sw // 2, cy - sh // 2 - 2), "$", font=sf, fill=WHITE + (255,))
    return img


def _dots_bg(img: Image.Image, spacing: int = 44):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for x in range(0, W, spacing):
        for y in range(0, H, spacing):
            d.ellipse([x, y, x + 1, y + 1], fill=(255, 255, 255, 10))
    img.alpha_composite(ov)


def _rings(draw: ImageDraw.ImageDraw, cx: int, cy: int,
           r1: int, r2: int, rgb=ACCENT):
    draw.ellipse([cx - r1, cy - r1, cx + r1, cy + r1],
                 outline=(*rgb, 35), width=2)
    draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2],
                 outline=(*rgb, 18), width=1)


def _badge(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, bg=ACCENT):
    f = _font(17)
    bb = draw.textbbox((0, 0), text, font=f)
    tw = bb[2] - bb[0]
    pad_x, pad_y, r = 18, 10, 14
    w, h = tw + pad_x * 2, pad_y * 2 + (bb[3] - bb[1])
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=(*bg, 210))
    draw.text((x + pad_x, y + pad_y - 1), text, font=f, fill=WHITE)


# ── generators ───────────────────────────────────────────────────────────────

def generate_home(output: Path):
    img = Image.new("RGBA", (W, H), BG + (255,))
    _dots_bg(img)
    _glow(img, 920, 60, 380, ACCENT)
    _glow(img, 160, 520, 200, (80, 80, 180))

    draw = ImageDraw.Draw(img)
    # top accent line
    draw.rectangle([0, 0, W, 4], fill=ACCENT)

    # SS14 logo
    logo = _ss14_logo(150)
    img.paste(logo, (80, 220), logo)
    draw = ImageDraw.Draw(img)

    # title block — vertically centred
    tx = 270
    draw.text((tx, 198), "Мини-станция", font=_font(74, True), fill=WHITE)
    draw.text((tx, 290), "Space Station 14", font=_font(30), fill=GREY)
    # accent tagline
    draw.text((tx, 342),
              "Некоммерческий сервер  ·  Роли  ·  Баталии  ·  Сообщество",
              font=_font(21), fill=ACCENT)

    # decorative rings bottom-right
    _rings(draw, 1080, 530, 200, 150)

    # domain badge
    _badge(draw, "ministation.ru", W - 210, H - 60)

    img.convert("RGB").save(str(output), "PNG", optimize=True)
    print(f"[OK] {output}  ({output.stat().st_size:,} bytes)")


def generate_donate(output: Path):
    img = Image.new("RGBA", (W, H), BG + (255,))
    _dots_bg(img)
    _glow(img, 240, 100, 320, ACCENT)
    _glow(img, 1020, 520, 200, (200, 50, 70))

    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 4], fill=ACCENT)

    # coin icon
    coin = _coin_icon(140)
    img.paste(coin, (80, 228), coin)
    draw = ImageDraw.Draw(img)

    tx = 260
    draw.text((tx, 198), "Поддержи проект", font=_font(70, True), fill=WHITE)
    draw.text((tx, 286), "Донат  —  Мини-станция", font=_font(28), fill=GREY)
    draw.text((tx, 336),
              "Подписки  ·  Discord-роли  ·  Цвет ника  ·  Монетки",
              font=_font(21), fill=ACCENT)

    _rings(draw, 1060, 140, 160, 110)
    _badge(draw, "ministation.ru/donate", W - 280, H - 60)

    img.convert("RGB").save(str(output), "PNG", optimize=True)
    print(f"[OK] {output}  ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    generate_home(STATIC / "og-default.png")
    generate_donate(STATIC / "og-donate.png")
