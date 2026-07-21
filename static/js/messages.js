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
                    ${chatAvatarHtml(d.avatar, 'dialog-avatar')}
                </div>
                <div class="dialog-body">
                    <div class="dialog-name-row">
                        <div class="dialog-name">${typeof profileLink === 'function' ? profileLink(d.other_id, d.nickname || 'Игрок', 'dialog-name-link') : escapeHtml(d.nickname || 'Игрок')}</div>
                        ${renderChatBadgesHtml(d.badges)}
                    </div>
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
                ${chatAvatarHtml(u.avatar, 'pm-user-avatar')}
                <span class="pm-user-main">
                    <span class="pm-user-name-row">
                        <span class="pm-user-name">${typeof profileLink === 'function' ? profileLink(u.player_id, u.game_nickname || u.discord_username, 'pm-user-name-link') : escapeHtml(u.game_nickname || u.discord_username)}</span>
                        ${renderChatBadgesHtml(u.badges)}
                    </span>
                    <span class="pm-user-sub">@${escapeHtml(u.discord_username || '')}</span>
                </span>
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

function formatPmTime(iso) {
    const d = new Date(iso);
    const now = new Date();
    if (d.toDateString() === now.toDateString()) {
        return d.toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
    });
}

function pmIsRead(value) {
    return value === 1 || value === true || value === '1';
}

function pmStatusHtml(own, read) {
    if (!own) return '';
    const isRead = pmIsRead(read);
    const cls = isRead ? 'dc-status dc-status-read' : 'dc-status dc-status-sent';
    // Не галочки: самолётик = отправлено, глаз = прочитано
    const icon = isRead ? 'fa-eye' : 'fa-paper-plane';
    const title = isRead ? 'Прочитано' : 'Отправлено';
    return `<span class="${cls}" title="${title}"><i class="fa-solid ${icon}"></i></span>`;
}

function renderPmMessage(m, myId, opts = {}) {
    const own = m.is_own === true || (myId && m.sender_id === myId);
    const text = m.content ?? m.message ?? m.text ?? '';
    const time = formatPmTime(m.created_at);
    const imageHtml = m.image_url ? renderChatImage(m.image_url, 'pm-msg-image') : '';
    const textHtml = text ? `<div class="dc-content">${formatMessageContent(text)}</div>` : '';
    const compact = !!opts.compact;
    const avatarHtml = compact
        ? '<div class="dc-avatar-spacer" aria-hidden="true"></div>'
        : (own
            ? chatAvatarHtml(currentUser?.avatar, 'pm-msg-avatar dc-avatar')
            : chatAvatarHtml(m.sender_avatar, 'pm-msg-avatar dc-avatar'));
    const name = own
        ? (currentUser?.display_name || currentUser?.username || 'Вы')
        : (m.sender_nickname || m.sender_name || 'Игрок');
    const nameHtml = own
        ? `<span class="dc-name dc-name-own">${escapeHtml(name)}</span>`
        : (typeof profileLink === 'function' && m.sender_id
            ? profileLink(m.sender_id, name, 'dc-name')
            : `<span class="dc-name">${escapeHtml(name)}</span>`);
    const badgesHtml = !own ? renderChatBadgesHtml(m.sender_badges) : '';

    if (!textHtml && !imageHtml) return '';

    return `<div class="dc-msg pm-message ${own ? 'own' : ''} ${compact ? 'dc-msg-compact' : ''}">
        ${avatarHtml}
        <div class="dc-body">
            ${compact ? '' : `<div class="dc-header">${nameHtml}${badgesHtml}<span class="dc-timestamp">${time}</span>${pmStatusHtml(own, m.read)}</div>`}
            ${compact ? `<div class="dc-compact-meta">${pmStatusHtml(own, m.read)}<span class="dc-timestamp">${time}</span></div>` : ''}
            ${textHtml}
            ${imageHtml ? `<div class="dc-attach">${imageHtml}</div>` : ''}
        </div>
    </div>`;
}

async function loadConversation(partnerId) {
    const container = document.getElementById('currentConversation');
    if (!container) return;
    try {
        const data = await apiCall('GET', `/api/messages/conversation/${partnerId}`);
        const messages = Array.isArray(data) ? data : (data.messages || []);
        const partner = Array.isArray(data) ? null : data.partner;
        const title = document.getElementById('conversationTitle');
        const titleText = title?.querySelector('.conversation-title-text');
        if (partner && titleText) {
            const name = partner.nickname || 'Диалог';
            const badges = renderChatBadgesHtml(partner.badges);
            const nameHtml = typeof profileLink === 'function'
                ? profileLink(partnerId, name, 'pm-title-link')
                : escapeHtml(name);
            titleText.innerHTML = `
                <span class="pm-title-avatar">${chatAvatarHtml(partner.avatar, 'pm-title-avatar-img')}</span>
                <span class="pm-title-main">${nameHtml}${badges}</span>
            `;
        }
        if (!messages.length) {
            container.innerHTML = '<p class="empty-state">Напишите первое сообщение</p>';
            return;
        }
        const myId = currentUser.social_id;
        const wasAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 48;
        const ordered = messages.reverse();
        container.innerHTML = ordered.map((m, i) => {
            const prev = i > 0 ? ordered[i - 1] : null;
            const sameAuthor = prev && (
                (prev.sender_id && prev.sender_id === m.sender_id)
                || (prev.is_own && m.is_own)
            );
            const gapMs = prev ? Math.abs(new Date(m.created_at) - new Date(prev.created_at)) : Infinity;
            const compact = sameAuthor && gapMs < 7 * 60 * 1000;
            return renderPmMessage(m, myId, { compact });
        }).join('');
        if (wasAtBottom) container.scrollTop = container.scrollHeight;
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
    if (typeof navigateTo === 'function') navigateTo('messages');
    else showSection('messages');
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
