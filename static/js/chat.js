let globalChatLastId = 0;
let globalChatPollInterval = null;
let globalChatInitialized = false;
let chatUserSearchTimeout = null;

function initGlobalChat() {
    if (!globalChatInitialized) {
        globalChatInitialized = true;
        loadGlobalChat(true);
        setupChatUserSearch();
        setupChatImagePreview('globalChatImage', 'globalChatImagePreview');
    }
    loadChatUsers('');
    startGlobalChatPolling();
}

function setupChatImagePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (!input || !preview || input.dataset.bound) return;
    input.dataset.bound = '1';
    input.addEventListener('change', () => {
        const file = input.files[0];
        if (!file) {
            preview.hidden = true;
            preview.innerHTML = '';
            return;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
            preview.hidden = false;
            preview.innerHTML = `<img src="${ev.target.result}" alt=""><button type="button" class="chat-preview-clear" onclick="clearChatImagePreview('${inputId}','${previewId}')"><i class="fa-solid fa-xmark"></i></button>`;
        };
        reader.readAsDataURL(file);
    });
}

function clearChatImagePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (input) input.value = '';
    if (preview) {
        preview.hidden = true;
        preview.innerHTML = '';
    }
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
                <button type="button" class="chat-user-main" onclick="event.stopPropagation(); openProfile(${JSON.stringify(u.player_id)})">
                    <img src="${u.avatar || '/static/default_avatar.png'}" class="chat-user-avatar" alt=""
                         onerror="this.src='/static/default_avatar.png'">
                    <div class="chat-user-info">
                        <div class="chat-user-name">${typeof profileLink === 'function' ? profileLink(u.player_id, u.game_nickname || u.discord_username, 'chat-user-name-link') : escapeHtml(u.game_nickname || u.discord_username)}</div>
                        <div class="chat-user-sub">@${escapeHtml(u.discord_username || '')}</div>
                    </div>
                </button>
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
    } else if (typeof navigateTo === 'function') {
        navigateTo('messages');
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
    const roleBadge = typeof renderRoleBadge === 'function' ? renderRoleBadge(m.author_role) : '';
    const authorBtn = typeof profileLink === 'function'
        ? profileLink(m.author_id, m.author_nickname, 'global-chat-author')
        : `<span class="global-chat-author">${escapeHtml(m.author_nickname)}</span>`;
    const textHtml = m.content ? `<div class="global-chat-text">${formatMessageContent(m.content)}</div>` : '';
    const imageHtml = renderChatImage(m.image_url);
    return `
        <div class="global-chat-message chat-bubble-row" data-id="${m.id}">
            ${avatar}
            <div class="global-chat-content">
                <div class="global-chat-meta">
                    ${authorBtn}${roleBadge}
                    <span class="global-chat-time">${time}</span>
                </div>
                <div class="chat-bubble-body">
                    ${textHtml}
                    ${imageHtml}
                </div>
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
    const imageInput = document.getElementById('globalChatImage');
    const message = input?.value.trim() || '';
    const file = imageInput?.files?.[0];
    if (!message && !file) return;

    const formData = new FormData();
    formData.append('message', message);
    if (file) formData.append('image', file);

    try {
        await apiCall('POST', '/api/chat', formData);
        if (input) input.value = '';
        clearChatImagePreview('globalChatImage', 'globalChatImagePreview');
        await loadGlobalChat(false);
    } catch (e) {
        alert(e.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    setupChatImagePreview('globalChatImage', 'globalChatImagePreview');
});
