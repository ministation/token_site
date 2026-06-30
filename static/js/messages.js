let currentPmPartnerId = null;
let pmSearchTimeout = null;

async function loadDialogs() {
    if (!currentUser?.player) {
        document.getElementById('dialogsList').innerHTML = '<p class="empty-state">Войдите, чтобы видеть сообщения</p>';
        return;
    }
    try {
        const dialogs = await apiCall('GET', '/api/messages/dialogs');
        const container = document.getElementById('dialogsList');
        if (!dialogs.length) {
            container.innerHTML = '<p class="empty-state">Нет диалогов — найдите игрока выше</p>';
            return;
        }
        container.innerHTML = dialogs.map(d => `
            <div class="dialog-item ${currentPmPartnerId === d.other_id ? 'active' : ''}"
                 onclick='openConversation(${JSON.stringify(d.other_id)}, ${JSON.stringify(d.nickname || 'Игрок')})'>
                <div class="dialog-name">${escapeHtml(d.nickname || 'Игрок')}</div>
                <div class="dialog-preview">${escapeHtml(d.last_msg || '')}</div>
                ${d.unread ? `<span class="dialog-unread">${d.unread}</span>` : ''}
            </div>
        `).join('');
    } catch (e) {
        document.getElementById('dialogsList').innerHTML = '<p class="error">Не удалось загрузить диалоги</p>';
    }
}

function setupPmUserSearch() {
    const input = document.getElementById('pmUserSearch');
    if (!input || input.dataset.bound) return;
    input.dataset.bound = '1';
    input.addEventListener('input', () => {
        clearTimeout(pmSearchTimeout);
        pmSearchTimeout = setTimeout(() => searchPmUsers(input.value), 300);
    });
}

async function searchPmUsers(query) {
    const container = document.getElementById('pmUserResults');
    if (!container) return;
    if (!query || query.trim().length < 2) {
        container.innerHTML = '';
        return;
    }
    if (!currentUser?.player) {
        container.innerHTML = '<p class="error">Войдите через Discord</p>';
        return;
    }
    try {
        const users = await apiCall('GET', '/api/messages/users?q=' + encodeURIComponent(query.trim()));
        if (!users.length) {
            container.innerHTML = '<p class="empty-state">Никого не найдено</p>';
            return;
        }
        container.innerHTML = users.map(u => `
            <button type="button" class="pm-user-item"
                onclick='startConversationWith(${JSON.stringify(u.player_id)}, ${JSON.stringify(u.game_nickname || u.discord_username || 'Игрок')})'>
                <span class="pm-user-name">${escapeHtml(u.game_nickname || u.discord_username)}</span>
                <span class="pm-user-sub">@${escapeHtml(u.discord_username || '')}</span>
            </button>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p class="error">Ошибка поиска</p>';
    }
}

async function openConversation(partnerId, nickname) {
    currentPmPartnerId = partnerId;
    const title = document.getElementById('conversationTitle');
    if (title) title.textContent = nickname || 'Диалог';
    const results = document.getElementById('pmUserResults');
    if (results) results.innerHTML = '';
    const search = document.getElementById('pmUserSearch');
    if (search) search.value = '';
    await loadDialogs();
    await loadConversation(partnerId);
}

async function loadConversation(partnerId) {
    const container = document.getElementById('currentConversation');
    if (!container) return;
    try {
        const messages = await apiCall('GET', `/api/messages/conversation/${partnerId}`);
        if (!messages.length) {
            container.innerHTML = '<p class="empty-state">Напишите первое сообщение</p>';
            return;
        }
        const myId = currentUser.player.player_id;
        const textKey = (m) => m.content ?? m.message ?? m.text ?? '';
        container.innerHTML = messages.reverse().map(m => {
            const own = m.sender_id === myId;
            return `<div class="pm-message ${own ? 'own' : ''}">
                <div class="pm-bubble">${escapeHtml(textKey(m))}</div>
                <div class="pm-time">${new Date(m.created_at).toLocaleString()}</div>
            </div>`;
        }).join('');
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        container.innerHTML = '<p class="error">Ошибка загрузки</p>';
    }
}

async function sendPrivateMessage() {
    if (!currentPmPartnerId) {
        alert('Выберите диалог или найдите игрока');
        return;
    }
    const input = document.getElementById('pmInput');
    const content = input?.value.trim();
    if (!content) return;
    try {
        await apiCall('POST', '/api/messages/send', {
            receiver_id: currentPmPartnerId,
            content
        });
        input.value = '';
        await loadConversation(currentPmPartnerId);
        await loadDialogs();
    } catch (e) {
        alert(e.message);
    }
}

function startConversationWith(playerId, nickname) {
    showSection('messages');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector('.nav-btn[data-section="messages"]');
    if (btn) btn.classList.add('active');
    if (typeof closeMobileNav === 'function') closeMobileNav();
    setupPmUserSearch();
    openConversation(playerId, nickname);
}

document.addEventListener('DOMContentLoaded', setupPmUserSearch);
