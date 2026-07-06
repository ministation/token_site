let onlineChart = null;
let currentOnlineMode = 'day';
let isInitialized = false;

function switchOnlineMode(mode, btn) {
    currentOnlineMode = mode;

    document.querySelectorAll('.chart-tab').forEach(b => b.classList.remove('active'));
    const activeBtn = btn || document.querySelector(`.chart-tab[data-mode="${mode}"]`);
    if (activeBtn) activeBtn.classList.add('active');
    
    const dayPicker = document.getElementById('dayPicker');
    if (dayPicker) {
        dayPicker.style.display = mode === 'day' ? 'inline-block' : 'none';
    }
    
    if (mode === 'day') {
        const date = dayPicker ? dayPicker.value : new Date().toISOString().slice(0, 10);
        loadDailyOnline(date);
    } else if (mode === 'weekly-hours') {
        loadWeeklyHourly();
    } else {
        loadOnlineChart('/api/online/' + mode);
    }
}

function initOnlineChart() {
    if (isInitialized) return;
    isInitialized = true;
    
    const dayPicker = document.getElementById('dayPicker');
    if (dayPicker) {
        dayPicker.valueAsDate = new Date();
    }
    
    setTimeout(() => {
        switchOnlineMode('day');
    }, 200);
}

async function loadDailyOnline(date) {
    try {
        const resp = await fetch('/api/online/day?date=' + date);
        const data = await resp.json();
        
        if (!data || data.length === 0) {
            return;
        }
        
        const labels = data.map(d => d.time);
        const avgValues = data.map(d => d.avg);
        const maxValues = data.map(d => d.max);
        
        renderChart(labels, avgValues, maxValues, 'Время (МСК)');
    } catch (e) {
        console.error('Error:', e);
    }
}

async function loadWeeklyHourly() {
    try {
        const resp = await fetch('/api/stats/weekly');
        const data = await resp.json();
        if (!data?.length) return;
        const labels = data.map(d => d.hour.slice(5, 16));
        const values = data.map(d => d.players);
        renderSingleChart(labels, values, 'Час (МСК)', 'Средний онлайн');
    } catch (e) {
        console.error('Error:', e);
    }
}

async function loadOnlineChart(url) {
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        
        if (!data || data.length === 0) {
            return;
        }
        
        const labels = data.map(d => d.date);
        const avgValues = data.map(d => d.avg);
        const maxValues = data.map(d => d.max);
        
        renderChart(labels, avgValues, maxValues, 'Дата');
    } catch (e) {
        console.error('Error:', e);
    }
}

function renderSingleChart(labels, values, xLabel, datasetLabel) {
    const canvas = document.getElementById('onlineChart');
    if (!canvas) return;
    sizeCanvas(canvas);
    const ctx = canvas.getContext('2d');
    if (onlineChart) { onlineChart.destroy(); onlineChart = null; }
    onlineChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: datasetLabel,
                data: values,
                backgroundColor: 'rgba(202, 165, 61, 0.55)',
                borderColor: '#caa53d',
                borderWidth: 1
            }]
        },
        options: chartOptions(xLabel)
    });
}

function sizeCanvas(canvas) {
    const wrap = canvas.closest('.chart-canvas-wrap') || canvas.parentElement;
    if (wrap) {
        canvas.width = Math.max(280, wrap.clientWidth - 8);
        canvas.height = Math.min(320, Math.max(220, window.innerWidth < 768 ? 240 : 300));
    }
}

function chartOptions(xLabel) {
    return {
        responsive: false,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
            legend: {
                position: 'top',
                labels: { color: '#ece2ca', padding: 12, font: { size: 11 } }
            }
        },
        scales: {
            x: {
                title: { display: true, text: xLabel, color: '#aaaaaa', font: { size: 11 } },
                ticks: { color: '#aaaaaa', maxRotation: 45, font: { size: 9 }, autoSkip: true, maxTicksLimit: 20 },
                grid: { color: 'rgba(255,255,255,0.05)' }
            },
            y: {
                beginAtZero: true,
                title: { display: true, text: 'Игроки', color: '#aaaaaa', font: { size: 11 } },
                ticks: { color: '#aaaaaa', stepSize: 1, precision: 0, font: { size: 10 } },
                grid: { color: 'rgba(255,255,255,0.05)' }
            }
        }
    };
}

function renderChart(labels, avgValues, maxValues, xLabel) {
    const canvas = document.getElementById('onlineChart');
    if (!canvas) return;
    sizeCanvas(canvas);
    const ctx = canvas.getContext('2d');
    if (onlineChart) { onlineChart.destroy(); onlineChart = null; }
    onlineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Средний',
                    data: avgValues,
                    borderColor: '#caa53d',
                    backgroundColor: 'rgba(202, 165, 61, 0.12)',
                    tension: 0.35,
                    fill: true,
                    pointRadius: 2,
                    borderWidth: 2
                },
                {
                    label: 'Максимум',
                    data: maxValues,
                    borderColor: '#6fbf73',
                    backgroundColor: 'rgba(111, 191, 115, 0.08)',
                    tension: 0.35,
                    fill: false,
                    pointRadius: 2,
                    borderWidth: 2
                }
            ]
        },
        options: chartOptions(xLabel)
    });
}

function destroyOnlineChart() {
    if (onlineChart) {
        onlineChart.destroy();
        onlineChart = null;
        isInitialized = false;
    }
}