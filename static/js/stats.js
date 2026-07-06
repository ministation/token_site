let playtimeChart = null;
let playtimeLoaded = false;

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
    if (typeof initOnlineChart === 'function') initOnlineChart();
}

window.addEventListener('themechange', () => {
    if (playtimeLoaded) loadPlaytimeChart();
});
