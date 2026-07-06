let playtimeChart = null;
let playtimeLoaded = false;
let adminRatingLoaded = false;

const STAR_ICON = '/static/icons/star.png';

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
        ? `<span class="admin-rating-value">${a.rating.toFixed(2)}</span>
           <img src="${STAR_ICON}" alt="" class="admin-rating-star">
           <span class="admin-rating-count">(${a.rating_count})</span>`
        : `<span class="admin-rating-value unknown">?</span>
           <img src="${STAR_ICON}" alt="" class="admin-rating-star">`;
    return `
        <div class="admin-rating-row">
            <div class="admin-rating-place">${a.place}</div>
            <div class="admin-rating-info">
                <div class="admin-rating-name">${escapeHtml(a.name)}</div>
                <div class="admin-rating-rank" style="--rank-color: ${a.rank_color}">
                    ${escapeHtml(a.rank_name)}${status}
                </div>
            </div>
            <div class="admin-rating-score">${rating}</div>
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

window.addEventListener('themechange', () => {
    if (playtimeLoaded) loadPlaytimeChart();
});
