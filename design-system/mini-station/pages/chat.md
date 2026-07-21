# Chat & Messages overrides

> Overrides `design-system/mini-station/MASTER.md` for messenger surfaces.

## Layout

- Global chat and PM are **app shells**, not stacked cards of messages.
- Grid: sidebar 280px + thread `1fr`, gap `0`, shared border.
- Thread column: `display:flex; flex-direction:column; min-height: calc(100vh - 200px)`.
- Messages area: `flex:1; min-height:0; overflow:auto` — never a fixed 360–480px max that feels cramped on desktop.

## Bubbles

- Only bubble chrome — remove padded outer cards per message.
- Gap between messages: 10–12px.
- Avatar 36px; author Exo 2 bold; body 0.95rem / 1.5.
- Own bubble: soft `--link` tint; peer: `--panel` on subtle `--panel-2` thread bg.

## Composer

- Sticky footer of thread column.
- Padding 12px 16px; gap 10px; align center.
- Controls 44×44; input height 44; send filled with accent or link blue for PM.
- Preview/emoji popovers sit above field (`bottom: calc(100% + 8px)`).

## Sidebar

- Search field full width, 40–44px tall.
- User/dialog rows 48px min, left-aligned avatar + text, 8px gap.
- Active dialog: inset accent bar 3px.

## Mobile

- Collapse to single column; users list max 160px high OR hide behind toggle.
- PM: sidebar/chat swap with `.chat-open` (existing).
- Composer tools may wrap; keep send reachable.
