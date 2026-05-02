let onlineChart = null;
let currentOnlineMode = 'day';
let isInitialized = false;

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

function renderChart(labels, avgValues, maxValues, xLabel) {
    const canvas = document.getElementById('onlineChart');
    if (!canvas) return;
    
    const container = canvas.parentElement;
    if (container) {
        canvas.width = container.clientWidth - 40;
        canvas.height = 300;
    }
    
    const ctx = canvas.getContext('2d');
    
    if (onlineChart) {
        onlineChart.destroy();
        onlineChart = null;
    }
    
    onlineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Средний',
                    data: avgValues,
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0,255,136,0.1)',
                    tension: 0.3,
                    fill: false,
                    pointRadius: 1,
                    borderWidth: 2
                },
                {
                    label: 'Максимум',
                    data: maxValues,
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255,107,107,0.1)',
                    tension: 0.3,
                    fill: false,
                    pointRadius: 1,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: false,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#cccccc',
                        padding: 15,
                        usePointStyle: true,
                        pointStyleWidth: 8,
                        font: { size: 11 }
                    }
                }
            },
            scales: {
                x: {
                    title: { 
                        display: true, 
                        text: xLabel, 
                        color: '#aaaaaa',
                        font: { size: 11 }
                    },
                    ticks: { 
                        color: '#aaaaaa',
                        maxRotation: 45,
                        font: { size: 9 },
                        autoSkip: true,
                        maxTicksLimit: 24
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    beginAtZero: true,
                    title: { 
                        display: true, 
                        text: 'Игроки', 
                        color: '#aaaaaa',
                        font: { size: 11 }
                    },
                    ticks: { 
                        color: '#aaaaaa',
                        stepSize: 1,
                        precision: 0,
                        font: { size: 10 }
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

function destroyOnlineChart() {
    if (onlineChart) {
        onlineChart.destroy();
        onlineChart = null;
        isInitialized = false;
    }
}