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

function profileLink(playerId, label, className = '') {
    if (!playerId) return escapeHtml(label || '');
    const cls = className ? ` class="${className}"` : '';
    return `<button type="button"${cls} onclick="openProfile(${JSON.stringify(playerId)})">${escapeHtml(label || 'Игрок')}</button>`;
}

function openProfile(playerId) {
    if (!playerId) return;
    showSection('profile');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector('.nav-btn[data-section="profile"]');
    if (btn) btn.classList.add('active');
    if (typeof closeMobileNav === 'function') closeMobileNav();
    if (typeof loadProfile === 'function') loadProfile(playerId);
}

function openMyProfile() {
    const id = currentUser?.social_id || currentPlayerId;
    if (!id) {
        alert('Войдите через Discord');
        return;
    }
    openProfile(id);
}
