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
                    ${chatAvatarHtml(u.avatar, 'chat-user-avatar')}
                    <div class="chat-user-info">
                        <div class="chat-user-name-row">
                            <div class="chat-user-name">${typeof profileLink === 'function' ? profileLink(u.player_id, u.game_nickname || u.discord_username, 'chat-user-name-link') : escapeHtml(u.game_nickname || u.discord_username)}</div>
                            ${renderChatBadgesHtml(u.badges)}
                        </div>
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
            container.innerHTML = messages.map((m, i) => {
                const prev = i > 0 ? messages[i - 1] : null;
                const sameAuthor = prev && prev.author_id === m.author_id;
                const gapMs = prev ? Math.abs(new Date(m.created_at) - new Date(prev.created_at)) : Infinity;
                const compact = sameAuthor && gapMs < 7 * 60 * 1000;
                return renderGlobalChatMessage(m, { compact });
            }).join('');
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

function formatChatTime(iso) {
    const d = new Date(iso);
    const now = new Date();
    if (d.toDateString() === now.toDateString()) {
        return d.toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
    });
}

function renderGlobalChatMessage(m, opts = {}) {
    const isOwn = !!(currentUser?.social_id && m.author_id === currentUser.social_id);
    const compact = !!opts.compact;
    const avatar = compact
        ? '<div class="dc-avatar-spacer" aria-hidden="true"></div>'
        : chatAvatarHtml(m.author_avatar, 'chat-avatar dc-avatar');
    const time = formatChatTime(m.created_at);
    const badgesHtml = renderChatBadgesHtml(m.author_badges || (
        typeof renderRoleBadge === 'function' && m.author_role
            ? [{ class: m.author_role === 'admin' ? 'admin-badge' : 'mod-badge', label: m.author_role === 'admin' ? 'ADMIN' : 'MOD' }]
            : []
    ));
    const authorBtn = typeof profileLink === 'function'
        ? profileLink(m.author_id, m.author_nickname, 'dc-name')
        : `<span class="dc-name">${escapeHtml(m.author_nickname)}</span>`;
    const textHtml = m.content ? `<div class="dc-content">${formatMessageContent(m.content)}</div>` : '';
    const imageHtml = m.image_url ? renderChatImage(m.image_url) : '';
    const statusHtml = isOwn
        ? '<span class="dc-status dc-status-sent" title="Отправлено"><i class="fa-solid fa-paper-plane"></i></span>'
        : '';

    return `
        <div class="dc-msg global-chat-message ${isOwn ? 'own' : ''} ${compact ? 'dc-msg-compact' : ''}" data-id="${m.id}" data-author-id="${escapeHtml(String(m.author_id || ''))}">
            ${avatar}
            <div class="dc-body">
                ${compact ? '' : `<div class="dc-header">${authorBtn}${badgesHtml}<span class="dc-timestamp">${time}</span>${statusHtml}</div>`}
                ${compact ? `<div class="dc-compact-meta">${statusHtml}<span class="dc-timestamp">${time}</span></div>` : ''}
                ${textHtml}
                ${imageHtml ? `<div class="dc-attach">${imageHtml}</div>` : ''}
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
