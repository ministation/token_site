function renderBadgesHtml(badges, extraClass = '') {
    if (!badges || !badges.length) return '';
    return badges.map(b => {
        const cls = [b.class, extraClass].filter(Boolean).join(' ');
        return `<span class="${escapeHtml(cls)}">${escapeHtml(b.label)}</span>`;
    }).join(' ');
}

function renderRoleBadge(role) {
    if (role === 'admin') return '<span class="admin-badge chat-role-badge">ADMIN</span>';
    if (role === 'moderator') return '<span class="mod-badge chat-role-badge">MOD</span>';
    return '';
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
