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
        stats: 'adminStatsTab', ratings: 'adminRatingsTab', posts: 'adminPostsTab',
        appeals: 'adminAppealsTab', compensation: 'adminCompensationTab',
        game: 'adminGameTab', playtime: 'adminPlaytimeTab',
        admins: 'adminAdminsTab'
    };
    const target = document.getElementById(map[tab]);
    if (target) target.style.display = 'block';
    document.querySelectorAll('.admin-tabs .tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'stats') loadAdminStats();
    if (tab === 'ratings') loadAdminRatingsPanel();
    if (tab === 'posts') loadAdminPostsList(false);
    if (tab === 'appeals') loadAdminAppeals(false);
    if (tab === 'compensation') loadAdminCompensation();
    if (tab === 'game') initGameModerationTab();
    if (tab === 'playtime' && typeof initPlaytimeTransfer === 'function') initPlaytimeTransfer();
    if (tab === 'admins') loadAdminList();
}

function canAccessAdminPanel() {
    return !!(currentUser?.is_admin || currentUser?.is_time_keeper);
}

function configureAdminTabsForUser() {
    const isAdmin = !!currentUser?.is_admin;
    const canPlaytime = canAccessAdminPanel();
    document.querySelectorAll('.admin-tabs .tab[data-admin-only]').forEach(el => {
        el.style.display = isAdmin ? '' : 'none';
    });
    document.querySelectorAll('.admin-tabs .tab[data-staff-only]').forEach(el => {
        el.style.display = canPlaytime ? '' : 'none';
    });
    const hint = document.querySelector('.admin-panel > .admin-hint');
    if (hint) {
        hint.textContent = isAdmin
            ? 'Управление сайтом — только для администраторов'
            : 'Перенос времени на роли — для хранителей времени';
    }
}

function initAdminPanel() {
    if (!canAccessAdminPanel()) return;
    const navBtn = document.getElementById('adminNavBtn');
    if (navBtn) navBtn.style.display = '';
    configureAdminTabsForUser();
    if (currentUser?.is_admin) {
        loadAdminStats();
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

async function loadAdminCompensation() {
    const statusEl = document.getElementById('adminCompensationStatus');
    if (!statusEl) return;
    try {
        const data = await apiCall('GET', '/api/admin/compensation');
        if (!data.active) {
            statusEl.innerHTML = '<p class="empty-state">Сейчас раздача компенсации не активна</p>';
            return;
        }
        const ends = data.ends_at ? new Date(data.ends_at).toLocaleString('ru-RU') : '—';
        statusEl.innerHTML = `
            <div class="stats-grid admin-stats-grid">
                <div class="stat-item"><div class="stat-value">${data.amount ?? 0}</div><div class="stat-label">Монет</div></div>
                <div class="stat-item"><div class="stat-value">${data.claims_count ?? 0}</div><div class="stat-label">Собрали</div></div>
                <div class="stat-item"><div class="stat-value">${formatCompensationAdminRemaining(data.remaining_seconds)}</div><div class="stat-label">Осталось</div></div>
            </div>
            <p class="admin-hint">До ${escapeHtml(ends)} · открыл ${escapeHtml(data.created_by || '—')}</p>`;
    } catch (e) {
        statusEl.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
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
