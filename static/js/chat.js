let globalChatLastId = 0;
let globalChatPollInterval = null;
let globalChatInitialized = false;
let chatUserSearchTimeout = null;

function initGlobalChat() {
    if (!globalChatInitialized) {
        globalChatInitialized = true;
        loadGlobalChat(true);
        setupChatUserSearch();
    }
    loadChatUsers('');
    startGlobalChatPolling();
}

function setupChatUserSearch() {
    const input = document.getElementById('chatUserSearch');
    if (!input || input.dataset.bound) return;
    input.dataset.bound = '1';
    input.addEventListener('input', () => {
        clearTimeout(chatUserSearchTimeout);
        chatUserSearchTimeout = setTimeout(() => loadChatUsers(input.value.trim()), 250);
    });
}

async function loadChatUsers(query) {
    const container = document.getElementById('chatUsersList');
    if (!container) return;
    if (!currentUser?.authenticated) {
        container.innerHTML = '<p class="empty-state">Войдите, чтобы видеть игроков</p>';
        return;
    }
    try {
        const users = await apiCall('GET', '/api/messages/users?q=' + encodeURIComponent(query || '') + '&limit=100');
        if (!users.length) {
            container.innerHTML = '<p class="empty-state">Никого не найдено</p>';
            return;
        }
        container.innerHTML = users.map(u => `
            <div class="chat-user-row">
                <img src="${u.avatar || '/static/default_avatar.png'}" class="chat-user-avatar" alt=""
                     onerror="this.src='/static/default_avatar.png'">
                <div class="chat-user-info">
                    <div class="chat-user-name">${escapeHtml(u.game_nickname || u.discord_username)}</div>
                    <div class="chat-user-sub">@${escapeHtml(u.discord_username || '')}</div>
                </div>
                <button type="button" class="chat-msg-btn" title="Написать"
                    onclick='messageUserFromChat(${JSON.stringify(u.player_id)}, ${JSON.stringify(u.game_nickname || u.discord_username || 'Игрок')})'>
                    <i class="fa-solid fa-envelope"></i>
                </button>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p class="error">Не удалось загрузить список</p>';
    }
}

function messageUserFromChat(playerId, nickname) {
    if (typeof startConversationWith === 'function') {
        startConversationWith(playerId, nickname);
    } else {
        showSection('messages');
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        const btn = document.querySelector('.nav-btn[data-section="messages"]');
        if (btn) btn.classList.add('active');
        if (typeof openConversation === 'function') openConversation(playerId, nickname);
    }
}

function startGlobalChatPolling() {
    stopGlobalChatPolling();
    globalChatPollInterval = setInterval(() => loadGlobalChat(false), 3000);
}

function stopGlobalChatPolling() {
    if (globalChatPollInterval) {
        clearInterval(globalChatPollInterval);
        globalChatPollInterval = null;
    }
}

async function loadGlobalChat(fullReload) {
    const container = document.getElementById('globalChatMessages');
    if (!container) return;
    try {
        const url = fullReload || !globalChatLastId
            ? '/api/chat'
            : '/api/chat?after=' + globalChatLastId;
        const res = await fetch(url);
        const messages = await res.json();
        if (!messages.length) {
            if (fullReload) {
                container.innerHTML = '<p class="empty-state">Чат пуст. Напишите первым!</p>';
            }
            return;
        }
        if (fullReload || !globalChatLastId) {
            container.innerHTML = messages.map(renderGlobalChatMessage).join('');
        } else {
            const empty = container.querySelector('.empty-state');
            if (empty) empty.remove();
            messages.forEach(m => {
                container.insertAdjacentHTML('beforeend', renderGlobalChatMessage(m));
            });
        }
        globalChatLastId = messages[messages.length - 1].id;
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        if (fullReload) container.innerHTML = '<p class="error">Не удалось загрузить чат</p>';
    }
}

function renderGlobalChatMessage(m) {
    const avatar = m.author_avatar
        ? `<img src="${m.author_avatar}" class="chat-avatar" alt="" onerror="this.style.display='none'">`
        : '<div class="chat-avatar chat-avatar-placeholder"><i class="fa-solid fa-user"></i></div>';
    const time = new Date(m.created_at).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
    });
    return `
        <div class="global-chat-message" data-id="${m.id}">
            ${avatar}
            <div class="global-chat-content">
                <div class="global-chat-meta">
                    <span class="global-chat-author">${escapeHtml(m.author_nickname)}</span>
                    <span class="global-chat-time">${time}</span>
                </div>
                <div class="global-chat-text">${escapeHtml(m.content)}</div>
            </div>
        </div>
    `;
}

async function sendGlobalChatMessage() {
    if (!currentUser?.authenticated) {
        alert('Войдите через Discord');
        return;
    }
    const input = document.getElementById('globalChatInput');
    const message = input?.value.trim();
    if (!message) return;
    try {
        await apiCall('POST', '/api/chat', { message });
        input.value = '';
        await loadGlobalChat(false);
    } catch (e) {
        alert(e.message);
    }
}
