let onlineChart = null;
let currentOnlineMode = 'day';

function switchOnlineMode(mode) {
    currentOnlineMode = mode;
    
    document.querySelectorAll('.chart-tab').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    const dayPicker = document.getElementById('dayPicker');
    if (dayPicker) {
        dayPicker.style.display = mode === 'day' ? 'inline-block' : 'none';
    }
    
    if (mode === 'day') {
        const date = dayPicker ? dayPicker.value : new Date().toISOString().slice(0, 10);
        loadDailyOnline(date);
    } else {
        loadOnlineChart('/api/online/' + mode, 'Дата');
    }
}

async function loadDailyOnline(date) {
    try {
        const resp = await fetch('/api/online/day?date=' + date);
        const data = await resp.json();
        
        if (!data || data.length === 0) {
            showEmptyChart('Нет данных за этот день');
            return;
        }
        
        const labels = data.map(d => d.hour);
        const avgValues = data.map(d => d.avg);
        const maxValues = data.map(d => d.max);
        
        renderOnlineChart(labels, [
            { label: 'Средний онлайн', data: avgValues, borderColor: '#3498db', backgroundColor: 'rgba(52,152,219,0.1)', tension: 0.3, fill: false },
            { label: 'Максимальный онлайн', data: maxValues, borderColor: '#e74c3c', backgroundColor: 'rgba(231,76,60,0.1)', tension: 0.3, fill: false }
        ], 'Час');
    } catch (e) {
        console.error('Online day error:', e);
    }
}

async function loadOnlineChart(url, xLabel) {
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        
        if (!data || data.length === 0) {
            showEmptyChart('Нет данных для отображения');
            return;
        }
        
        const labels = data.map(d => d.date);
        const avgValues = data.map(d => d.avg);
        const maxValues = data.map(d => d.max);
        
        renderOnlineChart(labels, [
            { label: 'Средний онлайн', data: avgValues, borderColor: '#3498db', backgroundColor: 'rgba(52,152,219,0.1)', tension: 0.3, fill: false },
            { label: 'Максимальный онлайн', data: maxValues, borderColor: '#e74c3c', backgroundColor: 'rgba(231,76,60,0.1)', tension: 0.3, fill: false }
        ], xLabel);
    } catch (e) {
        console.error('Online chart error:', e);
    }
}

function renderOnlineChart(labels, datasets, xLabel) {
    const canvas = document.getElementById('onlineChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    if (onlineChart) {
        onlineChart.destroy();
    }
    
    onlineChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#ccc',
                        padding: 15,
                        usePointStyle: true
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: xLabel, color: '#aaa' },
                    ticks: { color: '#aaa' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Игроки', color: '#aaa' },
                    ticks: { color: '#aaa', stepSize: 1 },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

function showEmptyChart(message) {
    const canvas = document.getElementById('onlineChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    if (onlineChart) {
        onlineChart.destroy();
    }
    
    onlineChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Нет данных'],
            datasets: [{ data: [0], backgroundColor: 'rgba(255,255,255,0.1)' }]
        },
        options: {
            plugins: {
                legend: { display: false },
                title: { display: true, text: message, color: '#888' }
            }
        }
    });
}

// Установка даты по умолчанию
document.addEventListener('DOMContentLoaded', () => {
    const dayPicker = document.getElementById('dayPicker');
    if (dayPicker) {
        dayPicker.valueAsDate = new Date();
    }
});