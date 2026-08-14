let adminUsersOffset = 0;
let adminPostsOffset = 0;
let adminUserSearchTimeout = null;
let gameBanSearchTimeout = null;
let gameJobsLoaded = false;
let gameJobsList = [];
let gameBansOffset = 0;
let gameSelectedPlayer = null;

function showAdminTab(tab, btn) {
    document.querySelectorAll('.admin-tab-content').forEach(el => el.style.display = 'none');
    const map = {
        stats: 'adminStatsTab', ratings: 'adminRatingsTab',
        inbox: 'adminInboxTab',
        appeals: 'adminInboxTab', tickets: 'adminInboxTab',
        compensation: 'adminCompensationTab',
        game: 'adminGameTab', playtime: 'adminPlaytimeTab',
        donations: 'adminDonationsTab',
        admins: 'adminAdminsTab'
    };
    const target = document.getElementById(map[tab]);
    if (target) target.style.display = 'block';
    document.querySelectorAll('.admin-tabs .tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'stats') loadAdminStats();
    if (tab === 'ratings') loadAdminRatingsPanel();
    if (tab === 'inbox' || tab === 'appeals' || tab === 'tickets') {
        if (typeof loadAdminInbox === 'function') loadAdminInbox();
    }
    if (tab === 'compensation') loadAdminCompensation();
    if (tab === 'game') initGameModerationTab();
    if (tab === 'playtime' && typeof initPlaytimeTransfer === 'function') initPlaytimeTransfer();
    if (tab === 'donations') {
        loadAdminDonationStats();
        loadAdminDonations();
    }
    if (tab === 'admins') loadAdminList();
}

function canAccessAdminPanel() {
    return !!(currentUser?.is_admin || currentUser?.is_time_keeper || currentUser?.is_moderator);
}

function configureAdminTabsForUser() {
    const isAdmin = !!currentUser?.is_admin;
    const isModerator = !!currentUser?.is_moderator;
    const canPlaytime = isAdmin || !!currentUser?.is_time_keeper;
    document.querySelectorAll('.admin-tabs .tab[data-admin-only]').forEach(el => {
        const modOk = el.hasAttribute('data-mod-ok');
        el.style.display = (isAdmin || (modOk && isModerator)) ? '' : 'none';
    });
    document.querySelectorAll('.admin-tabs .tab[data-staff-only]').forEach(el => {
        el.style.display = canPlaytime ? '' : 'none';
    });
    const hint = document.querySelector('.admin-panel > .admin-hint');
    if (hint) {
        if (isAdmin) {
            hint.textContent = 'Управление сайтом — только для администраторов';
        } else if (isModerator && !isAdmin) {
            hint.textContent = 'Игровая модерация и обжалования';
        } else {
            hint.textContent = 'Накрутка времени на роли — для хранителей времени';
        }
    }
}

function initAdminPanel() {
    if (!canAccessAdminPanel()) return;
    const navBtn = document.getElementById('adminNavBtn');
    if (navBtn) navBtn.style.display = '';
    configureAdminTabsForUser();
    if (currentUser?.is_admin) {
        loadAdminStats();
    } else if (currentUser?.is_moderator) {
        const gameBtn = document.querySelector('.admin-tabs .tab[data-mod-ok][onclick*="game"]');
        showAdminTab('game', gameBtn);
    } else {
        const playtimeBtn = document.querySelector('.admin-tabs .tab[data-staff-only]');
        showAdminTab('playtime', playtimeBtn);
    }
}

function debounceAdminUserSearch() {
    clearTimeout(adminUserSearchTimeout);
    adminUserSearchTimeout = setTimeout(() => loadAdminUsers(false), 300);
}

let adminRatingSelectedUuid = '';

function openAdminRatingsFor(userUuid) {
    if (typeof showSection === 'function') showSection('admin');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const navBtn = document.querySelector('.nav-btn[data-section="admin"]');
    if (navBtn) navBtn.classList.add('active');
    adminRatingSelectedUuid = userUuid || '';
    const tabBtn = document.querySelector('.admin-tabs .tab[onclick*="ratings"]');
    showAdminTab('ratings', tabBtn);
}

async function loadAdminRatingsPanel() {
    const select = document.getElementById('adminRatingSelect');
    const container = document.getElementById('adminRatingsContent');
    if (!select || !container) return;
    container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const leaders = await apiCall('GET', '/api/admin/admin-ratings/leaders');
        select.innerHTML = '<option value="">— Выберите администратора —</option>' +
            leaders.map(a => {
                const label = formatAdminRatingOptionLabel(a.name, a.rating, a.rating_count);
                return `<option value="${a.user_uuid}">${escapeHtml(label)}</option>`;
            }).join('');
        if (adminRatingSelectedUuid) {
            select.value = adminRatingSelectedUuid;
            await loadAdminRatingDetails(adminRatingSelectedUuid);
        } else {
            container.innerHTML = '<p class="empty-state">Выберите администратора, чтобы увидеть оценки</p>';
        }
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

function onAdminRatingSelectChange(uuid) {
    adminRatingSelectedUuid = uuid || '';
    if (!uuid) {
        const container = document.getElementById('adminRatingsContent');
        if (container) container.innerHTML = '<p class="empty-state">Выберите администратора, чтобы увидеть оценки</p>';
        return;
    }
    loadAdminRatingDetails(uuid);
}

async function loadAdminRatingDetails(userUuid) {
    const container = document.getElementById('adminRatingsContent');
    if (!container) return;
    container.innerHTML = '<p class="empty-state">Загрузка оценок...</p>';
    try {
        const data = await apiCall('GET', `/api/admin/admin-ratings/${encodeURIComponent(userUuid)}`);
        const admin = data.admin || {};
        const ratings = data.ratings || [];
        const summary = admin.rating_count > 0
            ? renderRatingDisplay(admin.rating, admin.rating_count, 'summary')
            : 'Оценок нет';
        if (!ratings.length) {
            container.innerHTML = `
                <div class="admin-rating-summary">${summary}</div>
                <p class="empty-state">У этого администратора нет оценок в базе</p>`;
            return;
        }
        container.innerHTML = `
            <div class="admin-rating-summary">${summary}</div>
            <div class="admin-rating-manage-list">
                ${ratings.map(r => `
                    <div class="admin-rating-manage-row">
                        <div class="admin-rating-manage-main">
                            <div class="admin-rating-manage-player">${escapeHtml(r.player_name)}</div>
                            <div class="admin-rating-manage-meta">
                                ${renderStarIcons(r.stars)}
                                <span class="admin-rating-manage-date">${r.created_at ? new Date(r.created_at).toLocaleString('ru-RU') : '—'}</span>
                                ${r.round_id != null ? `<span class="admin-rating-manage-round">#${r.round_id}</span>` : ''}
                            </div>
                        </div>
                        <button type="button" class="btn-danger-sm" title="Удалить оценку"
                            onclick="deleteAdminHelpRating(${r.id})">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                `).join('')}
            </div>`;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function refreshAdminRatingSelect() {
    const select = document.getElementById('adminRatingSelect');
    if (!select) return;
    const leaders = await apiCall('GET', '/api/admin/admin-ratings/leaders');
    const current = adminRatingSelectedUuid;
    select.innerHTML = '<option value="">— Выберите администратора —</option>' +
        leaders.map(a => {
            const label = formatAdminRatingOptionLabel(a.name, a.rating, a.rating_count);
            return `<option value="${a.user_uuid}">${escapeHtml(label)}</option>`;
        }).join('');
    if (current) select.value = current;
}

async function deleteAdminHelpRating(ratingId) {
    if (!currentUser?.is_admin) return;
    if (!confirm('Удалить эту оценку? Средний рейтинг администратора будет пересчитан в игровой БД.')) return;
    try {
        await apiCall('DELETE', `/api/admin/admin-ratings/${ratingId}`);
        await refreshAdminRatingSelect();
        if (adminRatingSelectedUuid) await loadAdminRatingDetails(adminRatingSelectedUuid);
        if (typeof refreshAdminRatingIfVisible === 'function') refreshAdminRatingIfVisible();
    } catch (e) {
        alert(e.message);
    }
}

async function loadAdminStats() {
    const container = document.getElementById('adminStatsContent');
    if (!container) return;
    try {
        const data = await apiCall('GET', '/api/admin/stats');
        const s = data.social || {};
        const v = data.visits || {};
        const g = data.game || {};
        const r = data.referral || {};
        const dailyRows = (v.daily || []).map(d => `
            <tr>
                <td>${escapeHtml(d.day || '')}</td>
                <td>${d.visits ?? 0}</td>
                <td>${d.visitors ?? 0}</td>
            </tr>
        `).join('');
        container.innerHTML = `
            <h3 class="admin-stats-heading"><i class="fa-solid fa-chart-simple"></i> Посещения сайта</h3>
            <div class="stats-grid admin-stats-grid admin-visits-grid">
                <div class="stat-item"><div class="stat-value">${v.visits_today ?? 0}</div><div class="stat-label">Просмотров сегодня</div></div>
                <div class="stat-item"><div class="stat-value">${v.visitors_today ?? 0}</div><div class="stat-label">Уникальных сегодня</div></div>
                <div class="stat-item"><div class="stat-value">${v.visits_7d ?? 0}</div><div class="stat-label">Просмотров за 7 дней</div></div>
                <div class="stat-item"><div class="stat-value">${v.visitors_7d ?? 0}</div><div class="stat-label">Уникальных за 7 дней</div></div>
                <div class="stat-item"><div class="stat-value">${v.visits_total ?? 0}</div><div class="stat-label">Просмотров всего</div></div>
                <div class="stat-item"><div class="stat-value">${v.visitors_total ?? 0}</div><div class="stat-label">Уникальных всего</div></div>
            </div>
            ${dailyRows ? `
            <div class="admin-visits-table-wrap table-scroll">
                <table class="admin-visits-table">
                    <thead><tr><th>День (МСК)</th><th>Просмотры</th><th>Уникальные</th></tr></thead>
                    <tbody>${dailyRows}</tbody>
                </table>
            </div>` : ''}
            <h3 class="admin-stats-heading"><i class="fa-solid fa-user-group"></i> Реферальная программа</h3>
            <div class="stats-grid admin-stats-grid">
                <div class="stat-item"><div class="stat-value">${r.referrals_total ?? 0}</div><div class="stat-label">Друзей приглашено</div></div>
                <div class="stat-item"><div class="stat-value">${r.referrers_active ?? 0}</div><div class="stat-label">Активных рефереров</div></div>
                <div class="stat-item"><div class="stat-value">${r.coins_distributed ?? 0}</div><div class="stat-label">Монет раздано</div></div>
                <div class="stat-item"><div class="stat-value">${r.coins_to_referrers ?? 0}</div><div class="stat-label">Пригласившим (+${r.referrer_reward ?? 5})</div></div>
                <div class="stat-item"><div class="stat-value">${r.coins_to_referees ?? 0}</div><div class="stat-label">Новым игрокам (+${r.referee_reward ?? 3})</div></div>
                ${(r.pending_coins ?? 0) > 0 ? `<div class="stat-item"><div class="stat-value">${r.pending_coins}</div><div class="stat-label">В очереди (без привязки)</div></div>` : ''}
            </div>
            <h3 class="admin-stats-heading"><i class="fa-solid fa-database"></i> Платформа</h3>
            <div class="stats-grid admin-stats-grid">
                <div class="stat-item"><div class="stat-value">${s.users ?? 0}</div><div class="stat-label">Пользователей</div></div>
                <div class="stat-item"><div class="stat-value">${s.posts ?? 0}</div><div class="stat-label">Постов</div></div>
                <div class="stat-item"><div class="stat-value">${s.comments ?? 0}</div><div class="stat-label">Комментариев</div></div>
                <div class="stat-item"><div class="stat-value">${s.private_messages ?? 0}</div><div class="stat-label">Личных сообщений</div></div>
                <div class="stat-item"><div class="stat-value">${s.chat_messages ?? 0}</div><div class="stat-label">Сообщений в чате</div></div>
                <div class="stat-item"><div class="stat-value">${s.admins ?? 0}</div><div class="stat-label">Админов</div></div>
                <div class="stat-item"><div class="stat-value">${g.total_players ?? 0}</div><div class="stat-label">Игроков (БД)</div></div>
                <div class="stat-item"><div class="stat-value">${g.total_tokens ?? 0}</div><div class="stat-label">Монет в обороте</div></div>
            </div>`;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

function formatCompensationAdminRemaining(seconds) {
    const sec = Math.max(0, seconds | 0);
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    if (h > 0) return `${h} ч ${m} мин`;
    if (m > 0) return `${m} мин`;
    return `${sec} сек`;
}

function formatCompensationDate(value) {
    if (!value) return '—';
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return escapeHtml(String(value));
    return dt.toLocaleString('ru-RU');
}

function renderAdminCompensationCurrent(current) {
    if (!current?.active) {
        return '<p class="empty-state">Сейчас раздача компенсации не активна</p>';
    }
    const ends = formatCompensationDate(current.ends_at);
    return `
        <h3 class="admin-stats-heading"><i class="fa-solid fa-bolt"></i> Текущая раздача</h3>
        <div class="stats-grid admin-stats-grid">
            <div class="stat-item"><div class="stat-value">${current.amount ?? 0}</div><div class="stat-label">Монет за сбор</div></div>
            <div class="stat-item"><div class="stat-value">${current.claims_count ?? 0}</div><div class="stat-label">Уже собрали</div></div>
            <div class="stat-item"><div class="stat-value">${formatCompensationAdminRemaining(current.remaining_seconds)}</div><div class="stat-label">Осталось</div></div>
        </div>
        <p class="admin-hint">До ${ends} · открыл ${escapeHtml(current.created_by || '—')}</p>`;
}

function renderAdminCompensationSummary(summary) {
    const s = summary || {};
    return `
        <div class="stats-grid admin-stats-grid">
            <div class="stat-item"><div class="stat-value">${s.total_giveaways ?? 0}</div><div class="stat-label">Раздач всего</div></div>
            <div class="stat-item"><div class="stat-value">${s.total_coins_distributed ?? 0}</div><div class="stat-label">Монет раздали</div></div>
            <div class="stat-item"><div class="stat-value">${s.total_claims ?? 0}</div><div class="stat-label">Сборов</div></div>
            <div class="stat-item"><div class="stat-value">${s.unique_players ?? 0}</div><div class="stat-label">Уникальных игроков</div></div>
        </div>`;
}

function renderAdminCompensationHistory(history) {
    const rows = history || [];
    if (!rows.length) {
        return '<p class="empty-state">История раздач пока пуста</p>';
    }
    return `
        <div class="admin-visits-table-wrap table-scroll compensation-history-table-wrap">
            <table class="admin-visits-table compensation-history-table">
                <thead>
                    <tr>
                        <th>Дата открытия</th>
                        <th>Окончание</th>
                        <th>Монет</th>
                        <th>Собрали</th>
                        <th>Раздали</th>
                        <th>Кто открыл</th>
                        <th>Статус</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(item => `
                        <tr>
                            <td>${formatCompensationDate(item.created_at)}</td>
                            <td>${formatCompensationDate(item.ends_at)}</td>
                            <td>${item.amount ?? 0}</td>
                            <td>${item.claims_count ?? 0}</td>
                            <td>${item.coins_distributed ?? 0}</td>
                            <td>${escapeHtml(item.created_by || '—')}</td>
                            <td><span class="compensation-status-badge ${item.is_active ? 'active' : 'ended'}">${item.is_active ? 'Активна' : 'Завершена'}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>`;
}

async function loadAdminCompensation() {
    const statusEl = document.getElementById('adminCompensationStatus');
    const summaryEl = document.getElementById('adminCompensationSummary');
    const historyEl = document.getElementById('adminCompensationHistory');
    if (!statusEl) return;
    if (summaryEl) summaryEl.innerHTML = '<p class="empty-state">Загрузка...</p>';
    if (historyEl) historyEl.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const data = await apiCall('GET', '/api/admin/compensation');
        statusEl.innerHTML = renderAdminCompensationCurrent(data.current || {});
        if (summaryEl) summaryEl.innerHTML = renderAdminCompensationSummary(data.summary);
        if (historyEl) historyEl.innerHTML = renderAdminCompensationHistory(data.history);
    } catch (e) {
        const err = `<p class="error">${escapeHtml(e.message)}</p>`;
        statusEl.innerHTML = err;
        if (summaryEl) summaryEl.innerHTML = err;
        if (historyEl) historyEl.innerHTML = err;
    }
}

async function startAdminCompensation() {
    const amount = parseInt(document.getElementById('adminCompensationAmount')?.value, 10);
    const duration = parseInt(document.getElementById('adminCompensationDuration')?.value, 10);
    const resultEl = document.getElementById('adminCompensationResult');
    if (!amount || amount < 1) {
        if (resultEl) resultEl.innerHTML = '<p class="error">Укажите сумму компенсации</p>';
        return;
    }
    if (!duration || duration < 1) {
        if (resultEl) resultEl.innerHTML = '<p class="error">Укажите длительность в минутах</p>';
        return;
    }
    try {
        await apiCall('POST', '/api/admin/compensation', {
            amount,
            duration_minutes: duration,
        });
        if (resultEl) resultEl.innerHTML = '<p class="success">Раздача компенсации открыта</p>';
        await loadAdminCompensation();
        if (typeof loadCompensation === 'function') loadCompensation();
    } catch (e) {
        if (resultEl) resultEl.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
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
                ${typeof chatAvatarHtml === 'function'
                    ? chatAvatarHtml(u.avatar, 'admin-user-avatar', u.presence || u.online_status || 'offline')
                    : `<img src="${u.avatar || '/static/default_avatar.png'}" class="admin-user-avatar" alt="">`}
                <div class="admin-user-info">
                    <div class="admin-user-name">${escapeHtml(u.game_nickname || u.discord_username)}
                        ${u.site_banned ? ' <span class="admin-badge" style="background:var(--danger)">BANNED</span>' : ''}
                    </div>
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
                ${typeof chatAvatarHtml === 'function'
                    ? chatAvatarHtml(p.author_avatar, 'admin-user-avatar', p.author_presence || 'offline')
                    : `<img src="${p.author_avatar || '/static/default_avatar.png'}" class="admin-user-avatar" alt="">`}
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
    if (typeof loadAdminInbox === 'function') return loadAdminInbox();
}

async function reviewAppeal(appealId, status) {
    if (typeof submitAppealDecision === 'function') {
        return submitAppealDecision(appealId, status);
    }
    const msg = status === 'approved'
        ? 'Одобрить обжалование и снять бан в игровой БД?\nКомментарий (необязательно):'
        : 'Причина отклонения:';
    const response = prompt(msg) || '';
    try {
        await apiCall('POST', `/api/admin/appeals/${appealId}/review`, { status, admin_response: response });
        if (typeof loadAdminInbox === 'function') loadAdminInbox();
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

function initGameModerationTab() {
    showGamePage('hub');
    if (!gameJobsLoaded) loadGameJobs();
    bindGameDurationPresets();
}

const GAME_PAGE_IDS = {
    hub: 'gamePageHub',
    player: 'gamePagePlayer',
    'server-ban': 'gamePageServerBan',
    'job-ban': 'gamePageJobBan',
    bans: 'gamePageBans',
};

function showGamePage(page, btn) {
    Object.entries(GAME_PAGE_IDS).forEach(([key, id]) => {
        const el = document.getElementById(id);
        if (el) el.hidden = key !== page;
    });
    document.querySelectorAll('.ss14-subnav-btn').forEach(b => {
        const activePage = page === 'player' ? 'hub' : page;
        b.classList.toggle('active', b.dataset.page === activePage);
    });
    if (page === 'bans') loadGameBans(false);
    updateGameSelectedChip();
}

async function copyGameText(text, btn) {
    if (!text) return;
    try {
        await navigator.clipboard.writeText(text);
        if (btn) {
            if (btn.classList.contains('ss14-copyable-ckey')) {
                btn.classList.add('ss14-copy-ok');
                setTimeout(() => btn.classList.remove('ss14-copy-ok'), 1400);
                return;
            }
            const icon = btn.querySelector('i');
            const prevClass = icon?.className;
            if (icon) icon.className = 'fa-solid fa-check';
            btn.classList.add('ss14-copy-ok');
            setTimeout(() => {
                if (icon && prevClass) icon.className = prevClass;
                btn.classList.remove('ss14-copy-ok');
            }, 1400);
        }
    } catch {
        alert('Не удалось скопировать');
    }
}

function shortUuid(uuid) {
    if (!uuid || uuid.length < 12) return uuid || '';
    return uuid.slice(0, 8) + '…';
}

function renderGamePlayerHit(p) {
    const name = p.name || 'Без ника';
    const selected = gameSelectedPlayer?.user_uuid === p.user_uuid;
    const safeName = escapeHtml(name);
    const safeUuid = escapeHtml(p.user_uuid);
    const nameJson = JSON.stringify(name);
    return `
        <div class="ss14-player-hit${selected ? ' is-selected' : ''}" data-uuid="${safeUuid}">
            <button type="button" class="ss14-player-hit-main" onclick="openPlayerDossier('${safeUuid}')">
                <span class="ss14-player-hit-name">${safeName}</span>
                <span class="ss14-player-hit-uuid" title="${safeUuid}">${escapeHtml(shortUuid(p.user_uuid))}</span>
            </button>
            <button type="button" class="ss14-copy-chip" title="Скопировать сикей"
                onclick="event.stopPropagation(); copyGameText(${nameJson}, this)">
                <i class="fa-regular fa-copy"></i>
            </button>
        </div>`;
}

async function openPlayerDossier(userUuid) {
    const container = document.getElementById('gamePlayerDossier');
    if (!container) return;
    showGamePage('player');
    container.innerHTML = '<p class="empty-state">Загрузка досье...</p>';
    try {
        const dossier = await apiCall('GET', `/api/admin/game/players/${encodeURIComponent(userUuid)}`);
        gameSelectedPlayer = dossier;
        applyGameSelectedPlayer(dossier);
        container.innerHTML = renderPlayerDossier(dossier);
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

function renderPlayerDossier(d) {
    const site = d.site_account || {};
    const name = d.name || 'Без ника';
    const nameJson = JSON.stringify(name);
    const activeBans = (d.bans || []).filter(b => b.is_active).length;

    const siteHtml = site.linked
        ? `<div class="ss14-dossier-site">
            <span class="ss14-dossier-site-badge ss14-dossier-site-badge--ok"><i class="fa-brands fa-discord"></i> Аккаунт привязан</span>
            <span>${escapeHtml(site.discord_username || site.game_nickname || '—')}</span>
            ${site.can_message && site.player_id && currentUser?.authenticated
                ? `<button type="button" class="btn-sm" onclick='messageUserFromChat(${JSON.stringify(site.player_id)}, ${JSON.stringify(name)})'>
                    <i class="fa-solid fa-envelope"></i> Написать
                   </button>`
                : ''}
           </div>`
        : `<div class="ss14-dossier-site"><span class="ss14-dossier-site-badge">Нет привязки к сайту</span></div>`;

    const chars = (d.characters || []).length
        ? d.characters.map(c => `
            <div class="ss14-dossier-char${c.is_selected ? ' is-selected' : ''}">
                <div class="ss14-dossier-char-head">
                    <strong>${escapeHtml(c.name)}</strong>
                    ${c.is_selected ? '<span class="ss14-dossier-pill">Активный</span>' : ''}
                    <span class="ss14-dossier-pill">Слот ${c.slot}</span>
                </div>
                <div class="ss14-dossier-char-meta">
                    ${escapeHtml([c.species, c.gender, c.age ? c.age + ' лет' : ''].filter(Boolean).join(' · '))}
                </div>
                ${c.flavor_text ? `<div class="ss14-dossier-flavor">${escapeHtml(c.flavor_text)}</div>` : ''}
            </div>`).join('')
        : '<p class="empty-state">Персонажи не найдены в БД</p>';

    const playtime = (d.playtime || []).length
        ? `<div class="ss14-dossier-playtime">${d.playtime.slice(0, 12).map(pt =>
            `<div class="ss14-dossier-pt-row"><span>${escapeHtml(pt.tracker)}</span><b>${pt.hours} ч</b></div>`
        ).join('')}</div>`
        : '<p class="empty-state">Нет данных о наигранном времени</p>';

    const notes = (d.notes || []).length
        ? d.notes.map(n => `
            <div class="ss14-dossier-note">
                <div class="ss14-dossier-note-head">
                    <span class="ss14-dossier-pill">${escapeHtml(n.type || 'note')}</span>
                    <span class="ss14-dossier-note-date">${n.created_at ? new Date(n.created_at).toLocaleString('ru-RU') : '—'}</span>
                </div>
                <div class="ss14-dossier-note-text">${escapeHtml(n.message)}</div>
            </div>`).join('')
        : '<p class="empty-state">Заметок администрации нет</p>';

    const bans = (d.bans || []).length
        ? d.bans.slice(0, 15).map(b => typeof renderAdminBanRow === 'function' ? renderAdminBanRow(b) : '').join('')
        : '<p class="empty-state">Банов нет</p>';

    return `
        <section class="ss14-dossier-hero">
            <div class="ss14-dossier-hero-main">
                <button type="button" class="ss14-copyable-name" onclick="copyGameText(${nameJson}, this)">
                    ${escapeHtml(name)} <i class="fa-regular fa-copy"></i>
                </button>
                <button type="button" class="ss14-copyable-uuid" onclick="copyGameText('${d.user_uuid}', this)">
                    ${escapeHtml(d.user_uuid)} <i class="fa-regular fa-copy"></i>
                </button>
                ${siteHtml}
            </div>
            <div class="ss14-dossier-actions">
                <button type="button" class="ss14-quick-btn ss14-quick-btn--server" onclick="showGamePage('server-ban')"><i class="fa-solid fa-ban"></i> Бан</button>
                <button type="button" class="ss14-quick-btn ss14-quick-btn--job" onclick="showGamePage('job-ban')"><i class="fa-solid fa-user-slash"></i> Джоббан</button>
                <button type="button" class="btn-sm" onclick="filterGameBansByPlayer('${d.user_uuid}'); showGamePage('bans')"><i class="fa-solid fa-filter"></i> Все баны</button>
            </div>
        </section>
        <div class="ss14-dossier-stats">
            <div class="ss14-player-stat"><b>${d.last_seen ? new Date(d.last_seen).toLocaleString('ru-RU') : '—'}</b>Последний визит</div>
            <div class="ss14-player-stat"><b>${escapeHtml(d.last_ip || '—')}</b>Последний IP</div>
            <div class="ss14-player-stat"><b>${activeBans}</b>Активных банов</div>
            <div class="ss14-player-stat"><b>${(d.bans || []).length}</b>Всего банов</div>
        </div>
        <section class="ss14-dossier-section">
            <h4><i class="fa-solid fa-user-astronaut"></i> Персонажи</h4>
            ${chars}
        </section>
        <section class="ss14-dossier-section">
            <h4><i class="fa-solid fa-clock"></i> Наигранное время</h4>
            ${playtime}
        </section>
        <section class="ss14-dossier-section">
            <h4><i class="fa-solid fa-clipboard"></i> Записи администрации</h4>
            ${notes}
        </section>
        <section class="ss14-dossier-section">
            <h4><i class="fa-solid fa-gavel"></i> Наказания</h4>
            <div class="ss14-ban-list">${bans}</div>
        </section>`;
}

function applyGameSelectedPlayer(player) {
    if (!player) return;
    const label = player.name || player.user_uuid;
    const serverInput = document.getElementById('serverBanPlayer');
    const roleInput = document.getElementById('roleBanPlayer');
    if (serverInput) serverInput.value = label;
    if (roleInput) roleInput.value = label;
    const results = document.getElementById('gamePlayerResults');
    if (results) {
        results.querySelectorAll('.ss14-player-hit').forEach(el => {
            el.classList.toggle('is-selected', el.dataset.uuid === player.user_uuid);
        });
    }
    updateGameSelectedChip();
}

function bindGameDurationPresets() {
    document.querySelectorAll('.ss14-duration-presets').forEach(group => {
        if (group.dataset.bound) return;
        group.dataset.bound = '1';
        const targetId = group.dataset.target;
        group.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-mins]');
            if (!btn || !targetId) return;
            const input = document.getElementById(targetId);
            if (input) input.value = btn.dataset.mins;
            group.querySelectorAll('button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
}

async function loadGameJobs() {
    const select = document.getElementById('roleBanJob');
    if (!select) return;
    try {
        gameJobsList = await apiCall('GET', '/api/admin/game/jobs');
        gameJobsLoaded = true;
        renderRoleBanJobOptions();
    } catch (e) {
        select.innerHTML = `<option value="" disabled>Ошибка: ${escapeHtml(e.message)}</option>`;
    }
}

function getRoleBanSelectedIds() {
    const select = document.getElementById('roleBanJob');
    if (!select) return [];
    return Array.from(select.selectedOptions).map(o => o.value).filter(Boolean);
}

function renderRoleBanJobOptions(filter = '') {
    const select = document.getElementById('roleBanJob');
    if (!select) return;
    const selected = new Set(getRoleBanSelectedIds());
    const q = filter.trim().toLowerCase();
    const jobs = q
        ? gameJobsList.filter(j => j.label.toLowerCase().includes(q) || j.id.toLowerCase().includes(q))
        : gameJobsList;
    if (!jobs.length) {
        select.innerHTML = '<option value="" disabled>Ничего не найдено</option>';
        return;
    }
    select.innerHTML = jobs.map(j => {
        const sel = selected.has(j.id) ? ' selected' : '';
        return `<option value="${escapeHtml(j.id)}"${sel}>${escapeHtml(j.label)}</option>`;
    }).join('');
}

function filterRoleBanJobs() {
    const filter = document.getElementById('roleBanJobFilter')?.value || '';
    renderRoleBanJobOptions(filter);
}

async function selectGamePlayer(userUuid) {
    await openPlayerDossier(userUuid);
}

function setGameSelectedPlayer(player) {
    gameSelectedPlayer = player;
    if (!player) {
        updateGameSelectedChip();
        return;
    }
    applyGameSelectedPlayer(player);
}

function updateGameSelectedChip() {
    const chip = document.getElementById('gameSelectedPlayerChip');
    if (!chip) return;
    if (!gameSelectedPlayer) {
        chip.hidden = true;
        chip.innerHTML = '';
        return;
    }
    const name = gameSelectedPlayer.name || 'Без ника';
    chip.hidden = false;
    chip.innerHTML = `
        <span class="ss14-selected-chip-label">Выбран:</span>
        <button type="button" class="ss14-selected-chip-name" title="Открыть досье"
            onclick="openPlayerDossier('${gameSelectedPlayer.user_uuid}')">
            ${escapeHtml(name)}
        </button>
        <button type="button" class="ss14-selected-chip-clear" onclick="clearGameSelectedPlayer()" title="Сбросить">
            <i class="fa-solid fa-xmark"></i>
        </button>`;
}

function clearGameSelectedPlayer() {
    gameSelectedPlayer = null;
    setGameSelectedPlayer(null);
    const serverInput = document.getElementById('serverBanPlayer');
    const roleInput = document.getElementById('roleBanPlayer');
    if (serverInput) serverInput.value = '';
    if (roleInput) roleInput.value = '';
}

async function searchGamePlayers() {
    const input = document.getElementById('gamePlayerSearch');
    const container = document.getElementById('gamePlayerResults');
    const q = input?.value.trim() || '';
    if (!container) return;
    if (q.length < 2) {
        container.innerHTML = '<p class="empty-state">Введите минимум 2 символа</p>';
        return;
    }
    container.innerHTML = '<p class="empty-state">Поиск...</p>';
    try {
        const players = await apiCall('GET', `/api/admin/game/players/search?q=${encodeURIComponent(q)}`);
        if (!players.length) {
            container.innerHTML = '<p class="empty-state">Игроки не найдены</p>';
            return;
        }
        container.innerHTML = players.map(p => renderGamePlayerHit(p)).join('');
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

function filterGameBansByPlayer(userUuid) {
    const hidden = document.getElementById('gameBanPlayerFilter');
    const clearBtn = document.getElementById('gameBanPlayerClear');
    const label = gameSelectedPlayer?.name || userUuid.slice(0, 8) + '…';
    if (hidden) hidden.value = userUuid;
    if (clearBtn) {
        clearBtn.style.display = '';
        clearBtn.innerHTML = `<i class="fa-solid fa-xmark"></i> ${escapeHtml(label)}`;
    }
    loadGameBans(false);
}

function clearGamePlayerBanFilter() {
    const hidden = document.getElementById('gameBanPlayerFilter');
    const clearBtn = document.getElementById('gameBanPlayerClear');
    if (hidden) hidden.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    loadGameBans(false);
}

function debounceGameBanSearch() {
    clearTimeout(gameBanSearchTimeout);
    gameBanSearchTimeout = setTimeout(() => loadGameBans(false), 300);
}

function renderAdminBanRow(b) {
    const isServer = b.type === 0;
    const rowClass = isServer ? 'type-server' : 'type-job';
    const badgeClass = isServer ? 'ban-type-badge--server' : 'ban-type-badge--job';
    const typeLabel = isServer ? 'Серверный' : 'Джоббан';
    const exp = b.expiration_time ? new Date(b.expiration_time).toLocaleString('ru-RU') : 'Навсегда';
    const time = b.ban_time ? new Date(b.ban_time).toLocaleString('ru-RU') : '—';
    const players = (b.player_names || []).length
        ? (b.player_names || []).map((name, i) => {
            const pid = (b.player_ids || [])[i];
            if (pid && typeof openPlayerDossier === 'function') {
                return `<button type="button" class="ss14-copyable-ckey" onclick="openPlayerDossier(${JSON.stringify(pid)})">${escapeHtml(name)}</button>`;
            }
            return escapeHtml(name);
        }).join(', ')
        : '—';
    const roles = (b.roles || []).join(', ');
    let status = '';
    if (b.is_unbanned) status = '<span class="ban-status ban-status-unbanned">Снят</span>';
    else if (b.is_active) status = '<span class="ban-status ban-status-active">Активен</span>';
    else status = '<span class="ban-status ban-status-expired">Истёк</span>';
    const unbanBtn = b.is_active
        ? `<button type="button" class="ss14-unban-btn" onclick="unbanGameBan(${b.ban_id})">
            <i class="fa-solid fa-unlock"></i> Разбанить
           </button>`
        : '';
    return `
        <article class="ss14-ban-row ${rowClass}">
            <div class="ss14-ban-row-main">
                <div class="ss14-ban-row-top">
                    <span class="ban-type-badge ${badgeClass}">${typeLabel}</span>
                    <span class="ss14-ban-row-id">#${b.ban_id}</span>
                    ${status}
                </div>
                <div class="ss14-ban-row-player">${players}</div>
                <div class="ss14-ban-row-meta">
                    <span><b>Выдан:</b> ${time}</span>
                    <span><b>Срок:</b> ${exp}</span>
                    <span><b>Админ:</b> ${escapeHtml(b.admin_name || '—')}</span>
                    ${roles ? `<span><b>Должности:</b> ${escapeHtml(roles)}</span>` : ''}
                    ${b.is_unbanned ? `<span><b>Снят:</b> ${b.unban_time ? new Date(b.unban_time).toLocaleString('ru-RU') : '—'}</span>` : ''}
                </div>
                <div class="ss14-ban-row-reason">${escapeHtml(b.reason || '—')}</div>
            </div>
            <div class="ss14-ban-row-actions">${unbanBtn}</div>
        </article>`;
}

async function loadGameBans(append) {
    const container = document.getElementById('gameBansContent');
    if (!container) return;
    if (!append) {
        gameBansOffset = 0;
        container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    }
    const type = document.getElementById('gameBanTypeFilter')?.value || '';
    const status = document.getElementById('gameBanStatusFilter')?.value || 'active';
    const q = document.getElementById('gameBanSearch')?.value.trim() || '';
    const player = document.getElementById('gameBanPlayerFilter')?.value.trim() || '';
    const params = new URLSearchParams({ limit: '25', offset: String(gameBansOffset), status });
    if (type !== '') params.set('ban_type', type);
    if (q) params.set('q', q);
    if (player) params.set('player', player);
    try {
        const bans = await apiCall('GET', `/api/admin/bans?${params}`);
        if (!append && !bans.length) {
            container.innerHTML = '<p class="empty-state">Банов не найдено</p>';
            return;
        }
        const html = bans.map(b => renderAdminBanRow(b)).join('');
        if (append) container.innerHTML += html;
        else container.innerHTML = html;
        gameBansOffset += bans.length;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function submitServerBan() {
    const player = document.getElementById('serverBanPlayer')?.value.trim();
    const reason = document.getElementById('serverBanReason')?.value.trim();
    const length_minutes = parseInt(document.getElementById('serverBanMinutes')?.value || '0', 10);
    const use_last_ip = !!document.getElementById('serverBanUseIp')?.checked;
    const result = document.getElementById('serverBanResult');
    if (!player || !reason) {
        if (result) result.innerHTML = '<p class="error">Укажите игрока и причину</p>';
        return;
    }
    if (result) result.innerHTML = '<p class="empty-state">Выдаём бан...</p>';
    try {
        const data = await apiCall('POST', '/api/admin/bans/server', {
            player, reason, length_minutes: Number.isFinite(length_minutes) ? length_minutes : 0, use_last_ip,
        });
        if (result) result.innerHTML = `<p class="success">Серверный бан #${data.ban_id} выдан</p>`;
        document.getElementById('serverBanReason').value = '';
        loadGameBans(false);
        if (gameSelectedPlayer) openPlayerDossier(gameSelectedPlayer.user_uuid);
    } catch (e) {
        if (result) result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function submitRoleBan() {
    const player = document.getElementById('roleBanPlayer')?.value.trim();
    const role_ids = getRoleBanSelectedIds();
    const reason = document.getElementById('roleBanReason')?.value.trim();
    const length_minutes = parseInt(document.getElementById('roleBanMinutes')?.value || '0', 10);
    const result = document.getElementById('roleBanResult');
    if (!player || !reason) {
        if (result) result.innerHTML = '<p class="error">Укажите игрока и причину</p>';
        return;
    }
    if (!role_ids.length) {
        if (result) result.innerHTML = '<p class="error">Выберите хотя бы одну должность</p>';
        return;
    }
    if (result) result.innerHTML = '<p class="empty-state">Выдаём джоббан...</p>';
    try {
        const data = await apiCall('POST', '/api/admin/bans/role', {
            player, role_ids, reason, length_minutes: Number.isFinite(length_minutes) ? length_minutes : 0,
        });
        const labels = (data.role_labels || role_ids).map(escapeHtml).join(', ');
        if (result) result.innerHTML = `<p class="success">Джоббан #${data.ban_id} выдан (${labels})</p>`;
        document.getElementById('roleBanReason').value = '';
        const select = document.getElementById('roleBanJob');
        if (select) Array.from(select.options).forEach(o => { o.selected = false; });
        loadGameBans(false);
        if (gameSelectedPlayer) openPlayerDossier(gameSelectedPlayer.user_uuid);
    } catch (e) {
        if (result) result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function unbanGameBan(banId) {
    if (!confirm(`Снять бан #${banId}?`)) return;
    try {
        await apiCall('POST', `/api/admin/bans/${banId}/unban`);
        loadGameBans(false);
        if (gameSelectedPlayer) openPlayerDossier(gameSelectedPlayer.user_uuid);
    } catch (e) {
        alert(e.message);
    }
}

async function loadAdminList() {
    const container = document.getElementById('adminListContent');
    if (!container) return;
    try {
        const [admins, badges] = await Promise.all([
            apiCall('GET', '/api/admin/admins'),
            apiCall('GET', '/api/admin/badges'),
        ]);
        const items = [];
        admins.forEach(a => {
            const roleBadge = a.role === 'moderator'
                ? '<span class="mod-badge">MOD</span>'
                : '<span class="admin-badge">ADMIN</span>';
            items.push({ discord_id: a.discord_id, username: a.discord_username || a.discord_id, badge: roleBadge, granted_by: a.granted_by, removable: true, revoke: 'admin' });
        });
        (badges.content_makers || []).forEach(a => {
            if (items.some(i => i.discord_id === a.discord_id)) return;
            items.push({ discord_id: a.discord_id, username: a.discord_username || a.discord_id, badge: '<span class="content-maker-badge">КОНТЕНТ</span>', granted_by: a.granted_by, removable: true, revoke: 'content' });
        });
        (badges.time_keepers || []).forEach(a => {
            if (items.some(i => i.discord_id === a.discord_id)) return;
            items.push({ discord_id: a.discord_id, username: a.discord_username || a.discord_id, badge: '<span class="time-keeper-badge">ХРАНИТЕЛЬ</span>', granted_by: a.granted_by, removable: true, revoke: 'time' });
        });
        if (!items.length) {
            container.innerHTML = '<p class="empty-state">Нет назначенного staff</p>';
            return;
        }
        container.innerHTML = items.map(a => `
            <div class="admin-list-item">
                <span><i class="fa-brands fa-discord"></i> ${escapeHtml(a.username)} ${a.badge}</span>
                <span class="admin-meta">назначил: ${escapeHtml(a.granted_by || '—')}</span>
                ${a.discord_id !== currentUser.discord_id
                    ? `<button type="button" class="btn-danger-sm" onclick="revokeStaffBadge('${a.discord_id}', '${a.revoke}')">Снять</button>`
                    : '<span class="admin-badge">Вы</span>'}
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function revokeStaffBadge(discordId, kind) {
    const labels = { admin: 'staff', content: 'контент-мейкера', time: 'хранителя времени' };
    if (!confirm(`Снять ${labels[kind] || 'права'}?`)) return;
    try {
        if (kind === 'content') await apiCall('DELETE', '/api/admin/content-makers/' + discordId);
        else if (kind === 'time') await apiCall('DELETE', '/api/admin/time-keepers/' + discordId);
        else await apiCall('DELETE', '/api/admin/admins/' + discordId);
        loadAdminList();
    } catch (e) {
        alert(e.message);
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
        if (res) res.innerHTML = `<p class="success">${
            role === 'admin' ? 'Администратор'
            : role === 'moderator' ? 'Модератор'
            : role === 'content_maker' ? 'Контент-мейкер'
            : 'Хранитель времени'
        } назначен</p>`;
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

async function loadAdminDonations() {
    const container = document.getElementById('adminDonationsList');
    if (!container) return;
    container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    const status = document.getElementById('adminDonationsStatus')?.value ?? 'awaiting_confirmation';
    const qs = status ? `?status=${encodeURIComponent(status)}&limit=50` : '?limit=50';
    try {
        const orders = await apiCall('GET', '/api/admin/donations' + qs);
        if (!orders.length) {
            container.innerHTML = '<p class="empty-state">Заказов нет</p>';
            return;
        }
        container.innerHTML = orders.map(o => {
            const canConfirm = o.status === 'awaiting_confirmation' || o.status === 'pending';
            const canReceipt = o.status === 'confirmed' && !o.receipt_uuid;
            const hasReceipt = !!o.receipt_uuid;
            const receiptErr = o.receipt_status === 'error';
            let receiptHtml = '';
            if (hasReceipt) {
                receiptHtml = `<a class="btn-sm" href="${escapeHtml(o.receipt_pdf_url || o.receipt_url || '#')}" target="_blank" rel="noopener">
                    <i class="fa-solid fa-file-pdf"></i> Чек PDF</a>`;
            } else if (canReceipt || receiptErr) {
                receiptHtml = `<button type="button" class="btn-sm" onclick='adminIssueDonationReceipt(${JSON.stringify(o.transaction_id)})'>
                    <i class="fa-solid fa-receipt"></i> ${receiptErr ? 'Повторить чек' : 'Выдать чек'}</button>`;
            }
            const errLine = receiptErr && o.receipt_error
                ? `<div class="admin-user-sub" style="color:var(--danger)">Чек: ${escapeHtml(o.receipt_error)}</div>`
                : '';
            return `
            <div class="admin-user-row">
                <div class="admin-user-info">
                    <div class="admin-user-name">${escapeHtml(o.tier_name || '')} · ${o.amount_rub || 0} ₽
                        <span class="admin-badge">${escapeHtml(o.status || '')}</span>
                        ${o.fulfilled ? '<span class="admin-badge">OK</span>' : ''}
                        ${hasReceipt ? '<span class="admin-badge">чек</span>' : ''}
                    </div>
                    <div class="admin-user-sub">
                        ${escapeHtml(o.product_type || '')}
                        · ${escapeHtml(o.contact || '—')}
                        · ${o.created_at ? new Date(o.created_at).toLocaleString('ru-RU') : ''}
                        · <code>${escapeHtml((o.transaction_id || '').slice(0, 8))}…</code>
                    </div>
                    ${errLine}
                </div>
                <div class="admin-donate-row-actions">
                ${canConfirm ? `
                    <button type="button" class="btn-sm" onclick='adminConfirmDonation(${JSON.stringify(o.transaction_id)})'>
                        <i class="fa-solid fa-check"></i> Оплата подтверждена
                    </button>` : ''}
                ${receiptHtml}
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

function onAdminDonatePeriodChange() {
    const period = document.getElementById('adminDonatePeriod')?.value || 'month';
    const custom = period === 'custom';
    const from = document.getElementById('adminDonateFrom');
    const to = document.getElementById('adminDonateTo');
    if (from) from.hidden = !custom;
    if (to) to.hidden = !custom;
    if (!custom) loadAdminDonationStats();
}

async function loadAdminDonationStats() {
    const box = document.getElementById('adminDonateStats');
    const breakdown = document.getElementById('adminDonateBreakdown');
    const nalogEl = document.getElementById('adminDonateNalogStatus');
    if (!box) return;
    const period = document.getElementById('adminDonatePeriod')?.value || 'month';
    let qs = `?period=${encodeURIComponent(period)}`;
    if (period === 'custom') {
        const from = document.getElementById('adminDonateFrom')?.value || '';
        const to = document.getElementById('adminDonateTo')?.value || '';
        if (!from || !to) {
            box.innerHTML = '<p class="empty-state">Укажите даты</p>';
            return;
        }
        qs = `?date_from=${encodeURIComponent(from)}&date_to=${encodeURIComponent(to)}`;
    }
    box.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const s = await apiCall('GET', '/api/admin/donations/stats' + qs);
        if (nalogEl) {
            nalogEl.textContent = s.nalog?.configured
                ? `Мой налог: подключен · авто-чек ${s.nalog.auto_receipt ? 'вкл' : 'выкл'} · ставка ${(Number(s.tax_rate) * 100).toFixed(0)}%`
                : 'Мой налог: не настроен (задайте NALOG_INN и NALOG_PASSWORD в .env) — чеки можно будет выдавать после настройки';
        }
        const fmt = (n) => Number(n || 0).toLocaleString('ru-RU');
        box.innerHTML = `
            <div class="stat-item"><div class="stat-value">${fmt(s.total_rub)} ₽</div><div class="stat-label">Выручка</div></div>
            <div class="stat-item"><div class="stat-value">${fmt(s.orders_count)}</div><div class="stat-label">Оплат</div></div>
            <div class="stat-item"><div class="stat-value">${fmt(s.unique_donors)}</div><div class="stat-label">Донатеров</div></div>
            <div class="stat-item"><div class="stat-value">${fmt(s.avg_check_rub)} ₽</div><div class="stat-label">Средний чек</div></div>
            <div class="stat-item"><div class="stat-value">${fmt(s.tax_estimate_rub)} ₽</div><div class="stat-label">НПД ~${(Number(s.tax_rate) * 100).toFixed(0)}%</div></div>
            <div class="stat-item"><div class="stat-value">${fmt(s.receipts?.issued || 0)}</div><div class="stat-label">Чеков НПД</div></div>
        `;
        if (breakdown) {
            const items = (s.by_item || []).slice(0, 8).map(r =>
                `<li><span>${escapeHtml(r.tier_name || '—')}</span><strong>${fmt(r.rub)} ₽</strong> <em>(${fmt(r.cnt)})</em></li>`
            ).join('') || '<li class="empty-state">Нет данных</li>';
            const donors = (s.top_donors || []).slice(0, 8).map(r =>
                `<li><span>${escapeHtml(r.contact || r.discord_id || r.donor_key || '—')}</span><strong>${fmt(r.total_rub)} ₽</strong> <em>(${fmt(r.orders_count)})</em></li>`
            ).join('') || '<li class="empty-state">Нет данных</li>';
            const days = (s.daily || []).slice(-14).map(r =>
                `<li><span>${escapeHtml(r.day || '')}</span><strong>${fmt(r.total_rub)} ₽</strong> <em>(${fmt(r.orders_count)})</em></li>`
            ).join('') || '<li class="empty-state">Нет данных</li>';
            breakdown.innerHTML = `
                <div class="admin-donate-cols">
                    <div>
                        <h4 class="admin-stats-heading">По товарам</h4>
                        <ul class="admin-donate-list">${items}</ul>
                    </div>
                    <div>
                        <h4 class="admin-stats-heading">Топ донатеров</h4>
                        <ul class="admin-donate-list">${donors}</ul>
                    </div>
                    <div>
                        <h4 class="admin-stats-heading">По дням</h4>
                        <ul class="admin-donate-list">${days}</ul>
                    </div>
                </div>
                <p class="admin-hint">Период: ${escapeHtml(s.date_from)} — ${escapeHtml(s.date_to)}.
                    Без чека: ${fmt(s.receipts?.missing || 0)}, ошибки чеков: ${fmt(s.receipts?.errors || 0)}.</p>
            `;
        }
    } catch (e) {
        box.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function adminConfirmDonation(txId) {
    if (!confirm('Подтвердить оплату и выдать привилегии (роль Discord / монеты за пакет)?')) return;
    try {
        await apiCall('POST', `/api/admin/donations/${encodeURIComponent(txId)}/confirm`);
        loadAdminDonations();
        loadAdminDonationStats();
    } catch (e) {
        alert(e.message);
    }
}

async function adminIssueDonationReceipt(txId) {
    if (!confirm('Создать чек в «Мой налог» по этой оплате?')) return;
    try {
        await apiCall('POST', `/api/admin/donations/${encodeURIComponent(txId)}/receipt`, {});
        loadAdminDonations();
        loadAdminDonationStats();
    } catch (e) {
        alert(e.message);
    }
}
