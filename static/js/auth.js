let currentUser = null;
let currentPlayerId = null;
const API_BASE = '';
const COIN_ICON = '<img src="/static/coin.png" class="coin-icon-result" alt="">';

async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE}/api/me`);
        const data = await res.json();
        currentUser = data;
        
        if (data.authenticated) {
            document.getElementById('loginBtn').style.display = 'none';
            const panel = document.getElementById('userPanel');
            panel.style.display = 'flex';
            panel.innerHTML = `
                ${data.avatar ? `<img src="${data.avatar}" alt="" onerror="this.style.display='none'">` : ''}
                <span id="userName">${data.display_name || data.username}</span>
                <button onclick="logout()">Выйти</button>
            `;
            if (data.player) {
                currentPlayerId = data.player.player_id;
            }
        } else {
            document.getElementById('loginBtn').style.display = 'block';
            document.getElementById('userPanel').style.display = 'none';
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }
}

function login() { window.location.href = `${API_BASE}/login`; }
function logout() { window.location.href = `${API_BASE}/logout`; }

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
        const err = await res.json();
        throw new Error(err.detail || 'Ошибка запроса');
    }
    return await res.json();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}