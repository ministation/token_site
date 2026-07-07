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

const STAR_ICON = '/static/icons/star.png';

function renderStarIcons(filled, max = 5) {
    const n = Math.max(0, Math.min(max, Number(filled) || 0));
    let html = `<span class="star-icons" aria-label="${n} из ${max}">`;
    for (let i = 0; i < max; i++) {
        html += i < n
            ? '<i class="fa-solid fa-star star-filled"></i>'
            : '<i class="fa-regular fa-star star-empty"></i>';
    }
    html += '</span>';
    return html;
}

function formatRatingCountChip(count) {
    const n = Number(count) || 0;
    if (n <= 0) return '';
    return `<span class="rating-count-chip" title="Количество оценок">
        <img src="${STAR_ICON}" alt="" class="admin-rating-star admin-rating-star-sm" aria-hidden="true">
        <span>${n}</span>
    </span>`;
}

function formatAdminRatingOptionLabel(name, rating, count) {
    const n = Number(count) || 0;
    if (n <= 0) return name;
    const score = rating != null ? Number(rating).toFixed(2) : '?';
    return `${name} · ${score} · ${n}★`;
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