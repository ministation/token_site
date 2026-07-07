let playtimeChart = null;
let playtimeLoaded = false;
let adminRatingLoaded = false;

function toggleAdminRatingPanel(btn) {
    const section = btn.closest('.collapsible-section');
    if (!section) return;
    const collapsed = section.classList.toggle('collapsed');
    btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
}

function messageAdminFromStats(playerId, nickname) {
    if (!currentUser?.authenticated) {
        alert('Войдите через Discord, чтобы писать сообщения');
        return;
    }
    if (typeof startConversationWith === 'function') {
        startConversationWith(playerId, nickname);
    }
}

async function loadAdminRating() {
    const container = document.getElementById('adminRatingList');
    if (!container) return;
    try {
        const data = await apiCall('GET', '/api/stats/admin-rating');
        const admins = data.admins || [];
        if (!admins.length) {
            container.innerHTML = '<p class="empty-state">Нет администраторов в базе данных</p>';
            adminRatingLoaded = true;
            return;
        }
        const updated = data.updated_at
            ? new Date(data.updated_at).toLocaleString('ru-RU', {
                day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
            })
            : '';
        container.innerHTML = `
            <div class="admin-rating-table">
                ${admins.map(a => renderAdminRatingRow(a)).join('')}
            </div>
            ${updated ? `<p class="admin-rating-updated">Обновлено: ${updated}</p>` : ''}`;
        adminRatingLoaded = true;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

function renderAdminRatingRow(a) {
    const status = a.suspended
        ? '<span class="admin-rating-status suspended">suspended</span>'
        : (a.deadminned ? '<span class="admin-rating-status deadmin">deadmin</span>' : '');
    const rating = a.rating_count > 0
        ? `<div class="admin-rating-score-inner">
               <span class="admin-rating-value">${a.rating.toFixed(2)}</span>
               <img src="${STAR_ICON}" alt="" class="admin-rating-star" aria-hidden="true">
               ${formatRatingCountChip(a.rating_count)}
           </div>`
        : `<span class="admin-rating-value unknown">—</span>`;
    const canMsg = a.can_message && a.player_id
        && currentUser?.authenticated
        && a.player_id !== currentUser.social_id;
    const msgBtn = canMsg
        ? `<button type="button" class="admin-rating-msg-btn" title="Написать"
            onclick='messageAdminFromStats(${JSON.stringify(a.player_id)}, ${JSON.stringify(a.name)})'>
            <i class="fa-solid fa-envelope"></i></button>`
        : '';
    const manageBtn = currentUser?.is_admin && a.rating_count > 0
        ? `<button type="button" class="admin-rating-msg-btn" title="Управление оценками"
            onclick='openAdminRatingsFor(${JSON.stringify(a.user_uuid)})'>
            <i class="fa-solid fa-sliders"></i></button>`
        : '';
    return `
        <div class="admin-rating-row">
            <div class="admin-rating-place">${a.place}</div>
            <div class="admin-rating-info">
                <div class="admin-rating-name">${escapeHtml(a.name)}</div>
                <div class="admin-rating-rank" style="--rank-color: ${a.rank_color}">
                    ${escapeHtml(a.rank_name)}${status}
                </div>
            </div>
            <div class="admin-rating-actions">
                <div class="admin-rating-score">${rating}</div>
                ${manageBtn}
                ${msgBtn}
            </div>
        </div>`;
}

async function loadPlaytimeChart() {
    const ctx = document.getElementById('playtimeCanvas');
    if (!ctx) return;
    try {
        const res = await fetch('/api/playtime-stats');
        const data = await res.json();
        if (playtimeChart) playtimeChart.destroy();
        const total = (data.newbies || 0) + (data.regulars || 0) + (data.veterans || 0);
        const totalEl = document.getElementById('playtimeTotal');
        if (totalEl) totalEl.textContent = 'Всего: ' + total + ' игроков (с онлайном > 5 ч)';
        playtimeChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [
                    'Новички (<50ч): ' + (data.newbies || 0),
                    'Обычные (50–400ч): ' + (data.regulars || 0),
                    'Ветераны (400+ч): ' + (data.veterans || 0)
                ],
                datasets: [{
                    data: [data.newbies || 0, data.regulars || 0, data.veterans || 0],
                    backgroundColor: [cssVar('--success'), cssVar('--gold'), cssVar('--accent')],
                    borderColor: cssVar('--panel'),
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: cssVar('--chart-text'), padding: 10, font: { size: 11 }, boxWidth: 12 }
                    }
                }
            }
        });
        playtimeLoaded = true;
    } catch (e) {
        console.error('Chart error:', e);
    }
}

function initStatsSection() {
    if (!playtimeLoaded) loadPlaytimeChart();
    if (!adminRatingLoaded) loadAdminRating();
    if (typeof initOnlineChart === 'function') initOnlineChart();
}

function refreshAdminRatingIfVisible() {
    if (!document.getElementById('adminRatingList')) return;
    adminRatingLoaded = false;
    loadAdminRating();
}

window.addEventListener('themechange', () => {
    if (playtimeLoaded) loadPlaytimeChart();
});
