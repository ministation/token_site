// Общие функции и переменные для всего сайта
const API_BASE = '';
const COIN_ICON = '<img src="/static/coin.png" class="coin-icon-result" alt="">';
let currentUser = null;
let currentPlayerId = null;

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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