function renderBadgesHtml(badges, extraClass = '') {
    if (!badges || !badges.length) return '';
    return badges.map(b => {
        const cls = [b.class, extraClass].filter(Boolean).join(' ');
        return `<span class="${escapeHtml(cls)}">${escapeHtml(b.label)}</span>`;
    }).join(' ');
}

function renderChatBadgesHtml(badges) {
    if (!badges || !badges.length) return '';
    return badges.map(b => {
        const cls = [b.class, 'chat-role-badge'].filter(Boolean).join(' ');
        return `<span class="${escapeHtml(cls)}">${escapeHtml(b.label)}</span>`;
    }).join(' ');
}

function renderRoleBadge(role) {
    return renderChatBadgesHtml(
        role === 'admin'
            ? [{ class: 'admin-badge', label: 'ADMIN' }]
            : role === 'moderator'
                ? [{ class: 'mod-badge', label: 'MOD' }]
                : []
    );
}

function normalizePresence(presence) {
    return ['online', 'idle', 'dnd', 'offline'].includes(presence) ? presence : 'offline';
}

function chatAvatarHtml(avatarUrl, className = 'chat-avatar', presence = 'offline') {
    const src = avatarUrl || '/static/default_avatar.png';
    const status = normalizePresence(presence);
    const titles = { online: 'В сети', idle: 'Не активен', dnd: 'Не беспокоить', offline: 'Не в сети' };
    const img = `<img src="${escapeHtml(src)}" class="${escapeHtml(className)}" alt="" onerror="this.onerror=null;this.src='/static/default_avatar.png'">`;
    return `<span class="dc-avatar-wrap" title="${titles[status]}"><span class="dc-avatar-mask">${img}</span><span class="dc-presence dc-presence-${status}" aria-label="${titles[status]}"></span></span>`;
}

function presenceDotHtml(presence) {
    const status = normalizePresence(presence);
    return `<span class="dc-presence dc-presence-${status}" aria-hidden="true"></span>`;
}

function profileHref(playerId) {
    if (!playerId) return '#/home';
    return `#/player/${encodeURIComponent(playerId)}`;
}

function profileLink(playerId, label, className = '') {
    if (!playerId) return escapeHtml(label || '');
    const cls = ['player-link', className].filter(Boolean).join(' ');
    return `<a href="${profileHref(playerId)}" class="${escapeHtml(cls)}">${escapeHtml(label || 'Игрок')}</a>`;
}

function openProfile(playerId) {
    if (!playerId) return;
    if (typeof closeMobileNav === 'function') closeMobileNav();
    if (typeof navigateTo === 'function') {
        navigateTo(`player/${encodeURIComponent(playerId)}`);
    }
}

document.addEventListener('click', (e) => {
    const link = e.target.closest('a.player-link');
    if (link) e.stopPropagation();
});

function openMyProfile() {
    const id = currentUser?.social_id || currentPlayerId;
    if (!id) {
        alert('Войдите через Discord');
        return;
    }
    openProfile(id);
}
