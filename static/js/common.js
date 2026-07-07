// Общие функции и переменные для всего сайта
const API_BASE = '';
const COIN_ICON = '<img src="/static/coin.png" class="coin-icon-result" alt="">';
let currentUser = null;
let currentPlayerId = null;

// Читает значение CSS-переменной текущей темы (для цветов графиков)
function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderStarIcons(filled, max = 5) {
    const n = Math.max(0, Math.min(max, Number(filled) || 0));
    let html = `<span class="star-icons" aria-hidden="true">`;
    for (let i = 0; i < max; i++) {
        html += i < n
            ? '<i class="fa-solid fa-star"></i>'
            : '<i class="fa-regular fa-star"></i>';
    }
    html += '</span>';
    return html;
}

function pluralizeRatings(n) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return 'оценка';
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'оценки';
    return 'оценок';
}

function renderRatingCountBadge(count) {
    const n = Number(count) || 0;
    if (n <= 0) return '';
    const label = pluralizeRatings(n);
    return `<span class="rating-display-count" title="${n} ${label}">
        <i class="fa-solid fa-comment-dots"></i>
        <span>${n}</span>
    </span>`;
}

function renderRatingDisplay(rating, count, variant = 'compact') {
    const n = Number(count) || 0;
    if (n <= 0) {
        return '<span class="rating-display rating-display--empty">—</span>';
    }
    const score = Number(rating).toFixed(2);
    const filled = Math.round(Number(rating));
    const label = pluralizeRatings(n);
    return `<div class="rating-display rating-display--${variant}" aria-label="Рейтинг ${score}, ${n} ${label}">
        <span class="rating-display-score">${score}</span>
        ${renderStarIcons(filled)}
        ${renderRatingCountBadge(n)}
    </div>`;
}

function formatAdminRatingOptionLabel(name, rating, count) {
    const n = Number(count) || 0;
    if (n <= 0) return name;
    const score = rating != null ? Number(rating).toFixed(2) : '?';
    return `${name} — ${score} · ${n} ${pluralizeRatings(n)}`;
}

async function apiCall(method, url, body = null) {
    const options = { method, headers: {} };
    if (body) {
        if (body instanceof FormData) {
            options.body = body;
        } else {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
    }
    const res = await fetch(`${API_BASE}${url}`, options);
    if (!res.ok) {
        let detail = 'Ошибка запроса';
        try {
            const err = await res.json();
            if (err && err.detail) detail = err.detail;
        } catch (e) { /* ответ не в формате JSON (например, страница ошибки) */ }
        throw new Error(detail);
    }
    return await res.json();
}