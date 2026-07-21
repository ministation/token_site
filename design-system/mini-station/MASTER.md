# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/mini-station/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Mini-station  
**Generated:** 2026-07-22 (ui-ux-pro-max, brand-adapted)  
**Category:** Gaming community / social hub (SS14)

---

## Direction

- **Pattern:** Community / Forum Landing — hero → activity → feed → join Discord  
- **Style:** Pixel Art + Soft UI Evolution (warm station HUD, not neon purple synthwave)  
- **Brand lock:** Amber / orange accent, light-first, optional dark theme  
- **Avoid:** AI purple gradients, CRT purple neon, cold minimal corporate, cream+terracotta cliché

---

## Color Palette (brand)

| Role | Light | Dark | CSS |
|------|-------|------|-----|
| Background | `#E8EEF7` | `#0A0F1E` | `--bg` |
| Panel / Card | `#FFFFFF` | `#141C33` | `--panel` |
| Panel muted | `#F1F5FB` | `#0F1628` | `--panel-2` |
| Ink | `#17222F` | `#E9EEF9` | `--ink` |
| Muted text | `#5A6B82` | `#9AA8C6` | `--muted` |
| Border | `#C9D4E4` | `#283355` | `--border` |
| Primary / Accent | `#F0780A` | `#FFB020` | `--accent` |
| Accent deep | `#D96508` | `#E68900` | `--accent-deep` |
| Secondary gold | `#FFC82E` | `#FFD54F` | `--accent-2` |
| Link | `#3D6EA8` | `#7EB3E8` | `--link` |
| Success | `#1F9A55` | `#38C273` | `--success` |
| Danger | `#D9453A` | `#EF6A5E` | `--danger` |
| Focus ring | accent glow | accent glow | `--accent-glow` |

**Hero gradient:** warm amber → orange (`--grad-hero`), never purple.

---

## Typography

- **Display / UI chrome:** `Press Start 2P` (`--font-pixel`) — logo, nav, card titles, buttons  
- **Body:** `Exo 2` (`--font-body`) — readable social text (prefer over VT323 for long copy)  
- Base size ≥ 16px equivalent; body line-height ≥ 1.5  
- Pixel headings stay small (0.55–0.75rem) to avoid overflow

```css
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Exo+2:wght@400;600;700&display=swap');
```

---

## Spacing & radius

| Token | Value |
|-------|-------|
| `--space-xs` | 4px |
| `--space-sm` | 8px |
| `--space-md` | 16px |
| `--space-lg` | 24px |
| `--radius` | 10px |
| `--radius-sm` | 6px |
| `--transition` | 180–220ms ease |

Touch targets ≥ 44×44px for primary controls.

---

## Motion

- Hover / press: 150–220ms  
- Ambient particles OK; respect `prefers-reduced-motion`  
- No decorative-only infinite glitch  
- Active press: slight translateY down (pixel “click”)

---

## Components

### Buttons
- Pixel font, hard offset shadow (`--shadow-btn`)  
- Visible `:focus-visible` ring using `--accent-glow`  
- Primary CTA: accent fill + white text  
- Discord: brand blue `#5865F2`

### Cards
- 2px border, hard shadow (`--shadow-hard`)  
- Title underline accent bar (64px)  
- Interactive lists: left-aligned rows, 36–44px avatars

### Navigation
- Sidebar groups with pixel titles  
- Active: accent fill, white icon  
- Mobile: drawer + backdrop

### Chat composer
- Single row, 44px controls aligned center  
- Tools / input / send same height

---

## Anti-patterns

- Purple-on-white or purple→indigo “AI default”  
- Gray-on-gray low contrast  
- `outline: none` without `:focus-visible`  
- Centering follower rows (avatars must column-align)  
- Animated RSI spritesheets as icons (use `icon.png`)  
- Emoji as UI icons (Font Awesome / SVG only)

---

## Pre-delivery checklist

- [ ] Contrast ≥ 4.5:1 (light + dark)  
- [ ] `cursor: pointer` on clickable controls  
- [ ] Hover + focus-visible states  
- [ ] `prefers-reduced-motion` respected  
- [ ] Responsive: 375 / 768 / 1024 / 1440  
- [ ] Brand name readable in first viewport  
- [ ] No horizontal scroll on mobile  
