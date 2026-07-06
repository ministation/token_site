let adminBansOffset = 0;
let adminUsersOffset = 0;
let adminPostsOffset = 0;
let adminUserSearchTimeout = null;

function showAdminTab(tab, btn) {
    document.querySelectorAll('.admin-tab-content').forEach(el => el.style.display = 'none');
    const map = {
        stats: 'adminStatsTab', users: 'adminUsersTab', posts: 'adminPostsTab',
        appeals: 'adminAppealsTab', bans: 'adminBansTab', admins: 'adminAdminsTab'
    };
    const target = document.getElementById(map[tab]);
    if (target) target.style.display = 'block';
    document.querySelectorAll('.admin-tabs .tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'stats') loadAdminStats();
    if (tab === 'users') loadAdminUsers(false);
    if (tab === 'posts') loadAdminPostsList(false);
    if (tab === 'appeals') loadAdminAppeals(false);
    if (tab === 'bans') loadAdminBans(false);
    if (tab === 'admins') loadAdminList();
}

function initAdminPanel() {
    if (!currentUser?.is_admin) return;
    const navBtn = document.getElementById('adminNavBtn');
    if (navBtn) navBtn.style.display = '';
    loadAdminStats();
}

function debounceAdminUserSearch() {
    clearTimeout(adminUserSearchTimeout);
    adminUserSearchTimeout = setTimeout(() => loadAdminUsers(false), 300);
}

async function loadAdminStats() {
    const container = document.getElementById('adminStatsContent');
    if (!container) return;
    try {
        const data = await apiCall('GET', '/api/admin/stats');
        const s = data.social || {};
        const g = data.game || {};
        const b = data.bank || {};
        container.innerHTML = `
            <div class="stats-grid admin-stats-grid">
                <div class="stat-item"><div class="stat-value">${s.users ?? 0}</div><div class="stat-label">Пользователей</div></div>
                <div class="stat-item"><div class="stat-value">${s.posts ?? 0}</div><div class="stat-label">Постов</div></div>
                <div class="stat-item"><div class="stat-value">${s.comments ?? 0}</div><div class="stat-label">Комментариев</div></div>
                <div class="stat-item"><div class="stat-value">${s.private_messages ?? 0}</div><div class="stat-label">Личных сообщений</div></div>
                <div class="stat-item"><div class="stat-value">${s.chat_messages ?? 0}</div><div class="stat-label">Сообщений в чате</div></div>
                <div class="stat-item"><div class="stat-value">${s.admins ?? 0}</div><div class="stat-label">Админов</div></div>
                <div class="stat-item"><div class="stat-value">${g.total_players ?? 0}</div><div class="stat-label">Игроков (БД)</div></div>
                <div class="stat-item"><div class="stat-value">${g.total_tokens ?? 0}</div><div class="stat-label">Монет в обороте</div></div>
                <div class="stat-item"><div class="stat-value">${b.total_deposits ?? 0}</div><div class="stat-label">Во вкладах</div></div>
                <div class="stat-item"><div class="stat-value">${b.total_loans ?? 0}</div><div class="stat-label">В займах</div></div>
            </div>`;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function loadAdminUsers(append) {
    const container = document.getElementById('adminUsersContent');
    if (!container) return;
    if (!append) { adminUsersOffset = 0; container.innerHTML = '<p class="empty-state">Загрузка...</p>'; }
    const q = document.getElementById('adminUserSearch')?.value.trim() || '';
    try {
        const data = await apiCall('GET', `/api/admin/users?q=${encodeURIComponent(q)}&limit=30&offset=${adminUsersOffset}`);
        const users = data.users || [];
        if (!append && !users.length) {
            container.innerHTML = '<p class="empty-state">Игроков не найдено</p>';
            return;
        }
        const html = users.map(u => `
            <div class="admin-user-row">
                <img src="${u.avatar || '/static/default_avatar.png'}" class="admin-user-avatar" alt="">
                <div class="admin-user-info">
                    <div class="admin-user-name">${escapeHtml(u.game_nickname || u.discord_username)}</div>
                    <div class="admin-user-sub">@${escapeHtml(u.discord_username || '')} · ${escapeHtml(u.player_id?.slice(0, 8) || '')}…</div>
                </div>
                ${u.is_admin ? '<span class="admin-badge">ADMIN</span>' : (u.is_moderator ? '<span class="mod-badge">MOD</span>' : '')}
                <button type="button" class="btn-sm" onclick='messageUserFromChat(${JSON.stringify(u.player_id)}, ${JSON.stringify(u.game_nickname || u.discord_username)})'>
                    <i class="fa-solid fa-envelope"></i>
                </button>
            </div>
        `).join('');
        if (append) container.innerHTML += html;
        else container.innerHTML = `<p class="admin-hint">Всего на платформе: ${data.total ?? users.length}</p>` + html;
        adminUsersOffset += users.length;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function loadAdminPostsList(append) {
    const container = document.getElementById('adminPostsList');
    if (!container) return;
    if (!append) { adminPostsOffset = 0; container.innerHTML = '<p class="empty-state">Загрузка...</p>'; }
    try {
        const posts = await apiCall('GET', `/api/admin/posts?limit=20&offset=${adminPostsOffset}`);
        if (!append && !posts.length) {
            container.innerHTML = '<p class="empty-state">Постов нет</p>';
            return;
        }
        const html = posts.map(p => {
            const section = p.category_label || 'Форум';
            const topic = p.topic_label ? ` · ${p.topic_label}` : '';
            const title = p.title ? `<strong>${escapeHtml(p.title)}</strong><br>` : '';
            return `
            <div class="admin-post-row">
                <img src="${p.author_avatar || '/static/default_avatar.png'}" class="admin-user-avatar" alt="">
                <div class="admin-post-body">
                    <div class="admin-post-meta">
                        <strong>#${p.id}</strong> · ${escapeHtml(section)}${escapeHtml(topic)}
                        · ${escapeHtml(p.author_discord || p.author_nickname)}
                        · ${new Date(p.created_at).toLocaleString()}
                        · ❤ ${p.like_count} · 💬 ${p.comment_count}
                    </div>
                    <div class="admin-post-text">${title}${escapeHtml(p.content)}</div>
                </div>
                <button type="button" class="btn-danger-sm" onclick="adminDeletePost(${p.id})"><i class="fa-solid fa-trash"></i></button>
            </div>`;
        }).join('');
        if (append) container.innerHTML += html;
        else container.innerHTML = html;
        adminPostsOffset += posts.length;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function loadAdminAppeals(append) {
    const container = document.getElementById('adminAppealsContent');
    if (!container) return;
    const status = document.getElementById('adminAppealFilter')?.value || '';
    if (!append) container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const url = '/api/admin/appeals?limit=50' + (status ? '&status=' + status : '');
        const appeals = await apiCall('GET', url);
        if (!appeals.length) {
            container.innerHTML = '<p class="empty-state">Обжалований нет</p>';
            return;
        }
        container.innerHTML = appeals.map(a => typeof renderAppealCard === 'function' ? renderAppealCard(a) : '').join('');
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function reviewAppeal(appealId, status) {
    const msg = status === 'approved'
        ? 'Одобрить обжалование и снять бан в игровой БД?\nКомментарий (необязательно):'
        : 'Причина отклонения:';
    const response = prompt(msg) || '';
    try {
        await apiCall('POST', `/api/admin/appeals/${appealId}/review`, { status, admin_response: response });
        if (document.getElementById('moderatorAppealsContent')) loadModeratorAppeals();
        if (document.getElementById('adminAppealsContent')) loadAdminAppeals(false);
    } catch (e) {
        alert(e.message);
    }
}

async function adminDeletePost(postId) {
    if (!currentUser?.is_admin) return;
    if (!confirm('Удалить пост #' + postId + '?')) return;
    try {
        await apiCall('DELETE', '/api/admin/posts/' + postId);
        loadAdminPostsList(false);
        if (typeof loadFeed === 'function') loadFeed();
    } catch (e) {
        alert(e.message);
    }
}

async function loadAdminBans(append) {
    const container = document.getElementById('adminBansContent');
    if (!container) return;
    if (!append) { adminBansOffset = 0; container.innerHTML = '<p class="empty-state">Загрузка...</p>'; }
    try {
        const bans = await apiCall('GET', `/api/admin/bans?limit=20&offset=${adminBansOffset}`);
        if (!append && !bans.length) {
            container.innerHTML = '<p class="empty-state">Банов нет</p>';
            return;
        }
        const html = bans.map(b => typeof renderBanCard === 'function' ? renderBanCard(b) : JSON.stringify(b)).join('');
        if (append) container.innerHTML += html;
        else container.innerHTML = html;
        adminBansOffset += bans.length;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function loadAdminList() {
    const container = document.getElementById('adminListContent');
    if (!container) return;
    try {
        const admins = await apiCall('GET', '/api/admin/admins');
        if (!admins.length) {
            container.innerHTML = '<p class="empty-state">Нет администраторов</p>';
            return;
        }
        container.innerHTML = admins.map(a => {
            const roleBadge = (a.role === 'moderator')
                ? '<span class="mod-badge">MOD</span>'
                : '<span class="admin-badge">ADMIN</span>';
            return `
            <div class="admin-list-item">
                <span><i class="fa-brands fa-discord"></i> ${escapeHtml(a.discord_username || a.discord_id)} ${roleBadge}</span>
                <span class="admin-meta">назначил: ${escapeHtml(a.granted_by || '—')}</span>
                ${a.discord_id !== currentUser.discord_id
                    ? `<button type="button" class="btn-danger-sm" onclick="revokeAdmin('${a.discord_id}')">Снять</button>`
                    : '<span class="admin-badge">Вы</span>'}
            </div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function grantAdmin() {
    const input = document.getElementById('adminGrantUsername');
    const roleSelect = document.getElementById('adminGrantRole');
    const username = input?.value.trim();
    const role = roleSelect?.value || 'admin';
    const res = document.getElementById('adminGrantResult');
    if (!username) { alert('Введите Discord-ник'); return; }
    try {
        await apiCall('POST', '/api/admin/admins', { discord_username: username, role });
        if (input) input.value = '';
        if (res) res.innerHTML = `<p class="success">${role === 'admin' ? 'Администратор' : 'Модератор'} назначен</p>`;
        loadAdminList();
    } catch (e) {
        if (res) res.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function revokeAdmin(discordId) {
    if (!confirm('Снять права администратора?')) return;
    try {
        await apiCall('DELETE', '/api/admin/admins/' + discordId);
        loadAdminList();
    } catch (e) {
        alert(e.message);
    }
}
