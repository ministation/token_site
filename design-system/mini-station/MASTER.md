# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/mini-station/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.

---

**Project:** Mini-station  
**Updated:** 2026-07-22 (ui-ux-pro-max redesign pass)  
**Category:** Gaming community / social hub (SS14)  
**Stack:** HTML + CSS (custom tokens)

---

## Direction

- **Pattern:** Community hub + messenger surfaces  
- **Style:** Soft UI Evolution + Micro-interactions + restrained Pixel Art chrome  
- **Brand:** Warm amber/orange, light-first, dark optional  
- **Feel:** Professional product UI — clear hierarchy, consistent 8pt spacing, calm surfaces  
- **Avoid:** Purple AI defaults, CRT neon overload, double-boxed chat bubbles, cramped max-heights, uneven gaps

---

## Spacing scale (8pt)

| Token | Value | Use |
|-------|-------|-----|
| `--space-xs` | 4px | Icon gaps |
| `--space-sm` | 8px | Tight stacks, chip gaps |
| `--space-md` | 16px | Card padding, list gaps |
| `--space-lg` | 24px | Section gaps |
| `--space-xl` | 32px | Page breathing room |

Layout rule: prefer `gap` over scattered margins. Cards use `p-16`/`p-20` internally; page sections stack with `gap-24`.

---

## Color (brand lock)

Keep existing amber tokens (`--accent #F0780A`, `--bg`, `--panel`, `--ink`, `--link`).  
Surfaces: white panels on cool-gray blue field. Borders 1px soft; accent used for active/CTA only.

---

## Typography

- Chrome: Press Start 2P (logo, nav labels, card H2, primary buttons) — keep small  
- Content: Exo 2 400/600/700 — chat, posts, forms (16px+, line-height 1.5)  
- Never use pixel font for message bodies

---

## Components

### Cards
- Radius 12px, 1px border, soft shadow (no heavy 4px hard offset on content cards)  
- Title + short hint, then content with consistent internal gap  
- One job per card

### Navigation
- 44px min height rows, 8px gap  
- Active = accent fill; hover = panel-3  
- Sidebar sticky with 16px group padding

### Chat / Messages (messenger pattern)
- App shell: header | (sidebar + thread) | composer sticky bottom  
- Thread fills remaining viewport (`min-height: calc(100vh - …)`, `max-height: none` inside flex)  
- Bubbles only — **no outer card around each message**  
- Own messages: soft link-tint; others: panel  
- Composer: single 44px row, 8–10px gaps, tools + field + send aligned  
- Touch: ≥8px between tools

### Motion
- 160–220ms hover/press  
- `prefers-reduced-motion` disables ambient + long transitions

---

## Pre-delivery

- [x] focus-visible rings  
- [x] cursor-pointer on clickables  
- [ ] Chat without double boxes  
- [ ] Consistent page gaps 16/24  
- [ ] Messenger height uses viewport flex, not tiny max-height  
- [ ] Mobile: 375 / 768 breakpoints, no horizontal scroll  
