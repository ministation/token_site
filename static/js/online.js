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
            { 
                label: 'Средний онлайн', 
                data: avgValues, 
                borderColor: '#00ff88', 
                backgroundColor: 'rgba(0,255,136,0.1)',
                tension: 0.2,
                fill: true,
                pointRadius: 3,
                pointBackgroundColor: '#00ff88',
                borderWidth: 2
            },
            { 
                label: 'Максимальный онлайн', 
                data: maxValues, 
                borderColor: '#ff6b6b', 
                backgroundColor: 'rgba(255,107,107,0.1)',
                tension: 0.2,
                fill: false,
                pointRadius: 3,
                pointBackgroundColor: '#ff6b6b',
                borderWidth: 2
            }
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
            { 
                label: 'Средний онлайн', 
                data: avgValues, 
                borderColor: '#00ff88', 
                backgroundColor: 'rgba(0,255,136,0.1)',
                tension: 0.2,
                fill: true,
                pointRadius: 3,
                pointBackgroundColor: '#00ff88',
                borderWidth: 2
            },
            { 
                label: 'Максимальный онлайн', 
                data: maxValues, 
                borderColor: '#ff6b6b', 
                backgroundColor: 'rgba(255,107,107,0.1)',
                tension: 0.2,
                fill: false,
                pointRadius: 3,
                pointBackgroundColor: '#ff6b6b',
                borderWidth: 2
            }
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
            animation: {
                duration: 300
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#cccccc',
                        padding: 20,
                        usePointStyle: true,
                        pointStyleWidth: 10,
                        font: {
                            size: 12
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { 
                        display: true, 
                        text: xLabel, 
                        color: '#aaaaaa',
                        font: { size: 12 }
                    },
                    ticks: { 
                        color: '#aaaaaa',
                        maxRotation: 45
                    },
                    grid: { 
                        color: 'rgba(255,255,255,0.08)' 
                    }
                },
                y: {
                    beginAtZero: true,
                    title: { 
                        display: true, 
                        text: 'Игроки', 
                        color: '#aaaaaa',
                        font: { size: 12 }
                    },
                    ticks: { 
                        color: '#aaaaaa',
                        stepSize: 1,
                        precision: 0
                    },
                    grid: { 
                        color: 'rgba(255,255,255,0.08)' 
                    }
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
                title: { 
                    display: true, 
                    text: message, 
                    color: '#aaaaaa',
                    font: { size: 14 }
                }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const dayPicker = document.getElementById('dayPicker');
    if (dayPicker) {
        dayPicker.valueAsDate = new Date();
    }
});