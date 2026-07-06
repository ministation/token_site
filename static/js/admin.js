let adminBansOffset = 0;

function showAdminTab(tab, btn) {
    document.querySelectorAll('.admin-tab-content').forEach(el => el.style.display = 'none');
    const map = { stats: 'adminStatsTab', posts: 'adminPostsTab', bans: 'adminBansTab', admins: 'adminAdminsTab' };
    const target = document.getElementById(map[tab]);
    if (target) target.style.display = 'block';
    document.querySelectorAll('.admin-tabs .tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'stats') loadAdminStats();
    if (tab === 'bans') loadAdminBans(false);
    if (tab === 'admins') loadAdminList();
}

function initAdminPanel() {
    if (!currentUser?.is_admin) return;
    const navBtn = document.getElementById('adminNavBtn');
    if (navBtn) navBtn.style.display = '';
    loadAdminStats();
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
                <div class="stat-item"><div class="stat-value">${s.sessions ?? 0}</div><div class="stat-label">Сессий</div></div>
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

async function adminDeletePost(postId) {
    if (!currentUser?.is_admin) return;
    if (!confirm('Удалить пост #' + postId + '?')) return;
    try {
        await apiCall('DELETE', '/api/admin/posts/' + postId);
        const el = document.querySelector('.post[data-post-id="' + postId + '"]');
        if (el) el.remove();
        if (typeof loadFeed === 'function') loadFeed();
    } catch (e) {
        alert(e.message);
    }
}

async function adminDeletePostById() {
    const id = parseInt(document.getElementById('adminDeletePostId')?.value);
    if (!id) { alert('Введите ID поста'); return; }
    await adminDeletePost(id);
    const res = document.getElementById('adminDeletePostResult');
    if (res) res.innerHTML = '<p class="success">Пост удалён</p>';
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
        container.innerHTML = admins.map(a => `
            <div class="admin-list-item">
                <span><i class="fa-brands fa-discord"></i> ${escapeHtml(a.discord_username || a.discord_id)}</span>
                <span class="admin-meta">назначил: ${escapeHtml(a.granted_by || '—')}</span>
                ${a.discord_id !== currentUser.discord_id
                    ? `<button type="button" class="btn-danger-sm" onclick="revokeAdmin('${a.discord_id}')">Снять</button>`
                    : '<span class="admin-badge">Вы</span>'}
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function grantAdmin() {
    const input = document.getElementById('adminGrantUsername');
    const username = input?.value.trim();
    const res = document.getElementById('adminGrantResult');
    if (!username) { alert('Введите Discord-ник'); return; }
    try {
        await apiCall('POST', '/api/admin/admins', { discord_username: username });
        if (input) input.value = '';
        if (res) res.innerHTML = '<p class="success">Администратор назначен</p>';
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
