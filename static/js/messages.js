let currentPmPartnerId = null;
let pmSearchTimeout = null;
let pmPollInterval = null;

async function loadDialogs() {
    const container = document.getElementById('dialogsList');
    if (!container) return;
    if (!currentUser?.authenticated) {
        container.innerHTML = '<p class="empty-state">Войдите, чтобы видеть сообщения</p>';
        return;
    }
    try {
        const dialogs = await apiCall('GET', '/api/messages/dialogs');
        if (!dialogs.length) {
            container.innerHTML = '<p class="empty-state">Нет диалогов — найдите игрока слева</p>';
            return;
        }
        container.innerHTML = dialogs.map(d => `
            <div class="dialog-item ${currentPmPartnerId === d.other_id ? 'active' : ''}"
                 onclick='openConversation(${JSON.stringify(d.other_id)}, ${JSON.stringify(d.nickname || 'Игрок')})'>
                <div class="dialog-avatar-wrap">
                    <div class="dialog-avatar-placeholder"><i class="fa-solid fa-user"></i></div>
                </div>
                <div class="dialog-body">
                    <div class="dialog-name">${escapeHtml(d.nickname || 'Игрок')}</div>
                    <div class="dialog-preview">${escapeHtml(d.last_msg || '')}</div>
                </div>
                ${d.unread ? `<span class="dialog-unread pixel-notify">${d.unread}</span>` : ''}
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p class="error">Не удалось загрузить диалоги</p>';
    }
}

function setupPmUserSearch() {
    const input = document.getElementById('pmUserSearch');
    if (!input || input.dataset.bound) return;
    input.dataset.bound = '1';
    input.addEventListener('input', () => {
        clearTimeout(pmSearchTimeout);
        pmSearchTimeout = setTimeout(() => searchPmUsers(input.value), 250);
    });
    input.addEventListener('focus', () => {
        if (!input.value.trim()) searchPmUsers('');
    });
}

async function searchPmUsers(query) {
    const container = document.getElementById('pmUserResults');
    if (!container) return;
    if (!currentUser?.authenticated) {
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
    const titleText = title?.querySelector('.conversation-title-text');
    if (titleText) {
        titleText.innerHTML = typeof profileLink === 'function'
            ? `<i class="fa-solid fa-user"></i> ${profileLink(partnerId, nickname || 'Диалог', 'pm-title-link')}`
            : `<i class="fa-solid fa-user"></i> ${escapeHtml(nickname || 'Диалог')}`;
    }
    const layout = document.getElementById('messagesLayout');
    if (layout) layout.classList.add('chat-open');
    const results = document.getElementById('pmUserResults');
    if (results) results.innerHTML = '';
    const search = document.getElementById('pmUserSearch');
    if (search) search.value = '';
    await loadConversation(partnerId);
    await loadDialogs();
    if (typeof pollNotifications === 'function') pollNotifications();
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
        const myId = currentUser.social_id;
        container.innerHTML = messages.reverse().map(m => {
            const own = m.is_own === true || (myId && m.sender_id === myId);
            const text = m.content ?? m.message ?? m.text ?? '';
            const time = new Date(m.created_at).toLocaleString('ru-RU', {
                day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
            });
            const textHtml = text ? `<div class="pm-bubble">${formatMessageContent(text)}</div>` : '';
            const imageHtml = renderChatImage(m.image_url, 'pm-msg-image');
            return `<div class="pm-message ${own ? 'own' : ''}">
                ${textHtml || imageHtml ? `<div class="pm-bubble-wrap">${textHtml}${imageHtml}</div>` : ''}
                <div class="pm-time">${time}</div>
            </div>`;
        }).join('');
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        container.innerHTML = '<p class="error">Ошибка загрузки</p>';
    }
}

async function sendPrivateMessage() {
    if (!currentUser?.authenticated) {
        alert('Войдите через Discord');
        return;
    }
    if (!currentPmPartnerId) {
        alert('Выберите диалог или найдите игрока');
        return;
    }
    const input = document.getElementById('pmInput');
    const imageInput = document.getElementById('pmImage');
    const content = input?.value.trim() || '';
    const file = imageInput?.files?.[0];
    if (!content && !file) return;

    const formData = new FormData();
    formData.append('receiver_id', currentPmPartnerId);
    formData.append('content', content);
    if (file) formData.append('image', file);

    try {
        await apiCall('POST', '/api/messages/send', formData);
        if (input) input.value = '';
        clearChatImagePreview('pmImage', 'pmImagePreview');
        await loadConversation(currentPmPartnerId);
        await loadDialogs();
        if (typeof pollNotifications === 'function') pollNotifications();
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
    if (typeof setupChatImagePreview === 'function') {
        setupChatImagePreview('pmImage', 'pmImagePreview');
    }
    startPmPolling();
    openConversation(playerId, nickname);
}

function startPmPolling() {
    stopPmPolling();
    pmPollInterval = setInterval(() => {
        if (currentPmPartnerId) loadConversation(currentPmPartnerId);
        loadDialogs();
        if (typeof pollNotifications === 'function') pollNotifications();
    }, 5000);
}

function stopPmPolling() {
    if (pmPollInterval) {
        clearInterval(pmPollInterval);
        pmPollInterval = null;
    }
}

function closePmConversation() {
    currentPmPartnerId = null;
    const layout = document.getElementById('messagesLayout');
    if (layout) layout.classList.remove('chat-open');
    const titleText = document.querySelector('#conversationTitle .conversation-title-text');
    if (titleText) titleText.innerHTML = '<i class="fa-solid fa-comments"></i> Выберите диалог';
    const container = document.getElementById('currentConversation');
    if (container) container.innerHTML = '<p class="empty-state">Выберите диалог или найдите игрока</p>';
    loadDialogs();
    if (typeof pollNotifications === 'function') pollNotifications();
}

document.addEventListener('DOMContentLoaded', () => {
    setupPmUserSearch();
    if (typeof setupChatImagePreview === 'function') {
        setupChatImagePreview('pmImage', 'pmImagePreview');
    }
});
