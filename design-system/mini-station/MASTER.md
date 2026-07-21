# Design System Master File

> Check `pages/[page].md` for overrides.

**Project:** Mini-station  
**Style:** Pixel Art (ui-ux-pro-max)  
**Updated:** 2026-07-22

## Typography (all pixel)

| Role | Font | Size notes |
|------|------|------------|
| UI chrome | Press Start 2P | nav, buttons, card titles — 0.5–0.65rem |
| Body / chat | VT323 | 18px base, ~1.15–1.25rem content |

Google Fonts: `Press+Start+2P` + `VT323`

## Buttons

- 2px border, hard offset shadow `0 3px 0`
- Hover: lift −1px; Active: press +2px, shadow none
- Min height ~42–44px
- Never flatten to 1px soft borders

## Chat

- Messenger shell, full viewport height
- Bubbles: 2px border, no outer card wrapper
- Images: **no border**, transparent bg
- Composer: align-items flex-end; preview stacks above input

## Color

Warm amber brand (`--accent #F0780A`). No purple neon defaults.
