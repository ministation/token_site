let onlineChart = null;
let currentOnlineMode = 'day';
let isInitialized = false;
let onlineChartMeta = null;
let onlineScrubberBound = false;
let onlineFocusedIndex = -1;

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

    bindOnlineScrubber();

    setTimeout(() => {
        switchOnlineMode('day');
    }, 200);
}

async function loadDailyOnline(date) {
    try {
        const resp = await fetch('/api/online/day?date=' + date);
        const data = await resp.json();

        if (!data || data.length === 0) {
            clearOnlineChartState('Нет данных за выбранный день');
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
        if (!data?.length) {
            clearOnlineChartState('Нет данных по часам');
            return;
        }
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
            clearOnlineChartState('Нет данных за период');
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

function isCoarsePointer() {
    return window.matchMedia('(pointer: coarse), (hover: none)').matches;
}

function clearOnlineChartState(message) {
    onlineChartMeta = null;
    hideOnlineReadout(message);
    hideOnlineScrubber();
}

function hideOnlineReadout(message) {
    const readout = document.getElementById('onlineChartReadout');
    const hint = document.getElementById('onlineChartHint');
    if (readout) readout.hidden = true;
    if (hint) {
        hint.textContent = message || 'Данные обновляются каждые 5 минут. Средний и пиковый онлайн.';
    }
}

function hideOnlineScrubber() {
    const wrap = document.getElementById('onlineScrubberWrap');
    if (wrap) wrap.hidden = true;
}

function bindOnlineScrubber() {
    if (onlineScrubberBound) return;
    const scrubber = document.getElementById('onlineChartScrubber');
    if (!scrubber) return;
    onlineScrubberBound = true;
    scrubber.addEventListener('input', () => {
        const index = Number(scrubber.value);
        focusOnlineIndex(index, { fromScrubber: true });
    });
}

function setupOnlineScrubber(labels) {
    const wrap = document.getElementById('onlineScrubberWrap');
    const scrubber = document.getElementById('onlineChartScrubber');
    const startEl = document.getElementById('onlineScrubberStart');
    const endEl = document.getElementById('onlineScrubberEnd');
    if (!wrap || !scrubber || !labels.length) {
        hideOnlineScrubber();
        return;
    }

    const showScrubber = isCoarsePointer() || labels.length > 16;
    wrap.hidden = !showScrubber;
    if (!showScrubber) return;

    scrubber.min = '0';
    scrubber.max = String(labels.length - 1);
    scrubber.step = '1';
    if (startEl) startEl.textContent = labels[0];
    if (endEl) endEl.textContent = labels[labels.length - 1];
}

function formatOnlineValue(value) {
    if (value == null || Number.isNaN(value)) return '—';
    return Number.isInteger(value) ? String(value) : Number(value).toFixed(1);
}

function updateOnlineReadout(index) {
    const meta = onlineChartMeta;
    const readout = document.getElementById('onlineChartReadout');
    const labelEl = document.getElementById('onlineReadoutLabel');
    const valuesEl = document.getElementById('onlineReadoutValues');
    const hint = document.getElementById('onlineChartHint');
    if (!meta || !readout || !labelEl || !valuesEl || index < 0 || index >= meta.labels.length) {
        return;
    }

    const label = meta.labels[index];
    readout.hidden = false;
    labelEl.textContent = label;

    if (meta.kind === 'single') {
        valuesEl.innerHTML = `<span class="online-readout-chip avg">Средний: <b>${formatOnlineValue(meta.values[index])}</b></span>`;
    } else {
        valuesEl.innerHTML = `
            <span class="online-readout-chip avg">Средний: <b>${formatOnlineValue(meta.avgValues[index])}</b></span>
            <span class="online-readout-chip max">Максимум: <b>${formatOnlineValue(meta.maxValues[index])}</b></span>`;
    }

    if (hint) {
        hint.textContent = isCoarsePointer()
            ? 'Проведите ползунком или коснитесь графика, чтобы выбрать время.'
            : 'Наведите на график или потяните ползунок, чтобы увидеть значения.';
    }
}

function focusOnlineIndex(index, opts = {}) {
    const meta = onlineChartMeta;
    if (!meta || index < 0 || index >= meta.labels.length) return;

    updateOnlineReadout(index);

    const scrubber = document.getElementById('onlineChartScrubber');
    if (scrubber && !opts.fromScrubber) {
        scrubber.value = String(index);
    }

    if (!onlineChart || (onlineFocusedIndex === index && !opts.force)) return;
    onlineFocusedIndex = index;

    const active = meta.kind === 'single'
        ? [{ datasetIndex: 0, index }]
        : [{ datasetIndex: 0, index }, { datasetIndex: 1, index }];
    onlineChart.setActiveElements(active);
    onlineChart.tooltip.setActiveElements(active, { x: 0, y: 0 });
    onlineChart.update('none');
}

function getNearestChartIndex(chart, clientX) {
    const rect = chart.canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const scale = chart.scales.x;
    if (!scale) return 0;

    const raw = scale.getValueForPixel(x);
    if (typeof raw === 'number' && Number.isFinite(raw)) {
        return Math.max(0, Math.min(chart.data.labels.length - 1, Math.round(raw)));
    }

    let best = 0;
    let bestDist = Infinity;
    for (let i = 0; i < chart.data.labels.length; i++) {
        const px = scale.getPixelForValue(i);
        const dist = Math.abs(px - x);
        if (dist < bestDist) {
            bestDist = dist;
            best = i;
        }
    }
    return best;
}

function attachOnlineChartInteraction(canvas) {
    if (canvas._onlineInteractionBound) return;
    canvas._onlineInteractionBound = true;

    let dragging = false;

    const pickFromEvent = (event) => {
        if (!onlineChart || !onlineChartMeta) return;
        const clientX = event.touches ? event.touches[0].clientX : event.clientX;
        const index = getNearestChartIndex(onlineChart, clientX);
        focusOnlineIndex(index);
    };

    canvas.addEventListener('pointerdown', (event) => {
        dragging = true;
        canvas.setPointerCapture?.(event.pointerId);
        pickFromEvent(event);
    });

    canvas.addEventListener('pointermove', (event) => {
        if (!dragging && event.pointerType === 'mouse') {
            pickFromEvent(event);
            return;
        }
        if (dragging) pickFromEvent(event);
    });

    canvas.addEventListener('pointerup', () => { dragging = false; });
    canvas.addEventListener('pointercancel', () => { dragging = false; });
    canvas.addEventListener('pointerleave', (event) => {
        if (event.pointerType === 'mouse' && !dragging) return;
        dragging = false;
    });
}

function renderSingleChart(labels, values, xLabel, datasetLabel) {
    const canvas = document.getElementById('onlineChart');
    if (!canvas) return;
    sizeCanvas(canvas);
    const ctx = canvas.getContext('2d');
    if (onlineChart) { onlineChart.destroy(); onlineChart = null; }

    onlineChartMeta = {
        kind: 'single',
        labels,
        values,
        xLabel,
        datasetLabel
    };
    onlineFocusedIndex = -1;

    setupOnlineScrubber(labels);
    const defaultIndex = Math.max(0, labels.length - 1);

    onlineChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: datasetLabel,
                data: values,
                backgroundColor: 'rgba(30, 111, 217, 0.45)',
                borderColor: cssVar('--accent'),
                borderWidth: 1,
                borderRadius: 3
            }]
        },
        options: buildChartOptions(xLabel, false)
    });

    attachOnlineChartInteraction(canvas);
    focusOnlineIndex(defaultIndex, { force: true });
}

function sizeCanvas(canvas) {
    const wrap = canvas.closest('.chart-canvas-wrap') || canvas.parentElement;
    if (wrap) {
        const mobile = window.innerWidth < 768;
        canvas.width = Math.max(280, wrap.clientWidth - 8);
        canvas.height = mobile ? 260 : Math.min(320, Math.max(220, 300));
    }
}

function buildChartOptions(xLabel, isLine) {
    const text = cssVar('--chart-text');
    const grid = cssVar('--chart-grid');
    const mobile = isCoarsePointer();

    return {
        responsive: false,
        maintainAspectRatio: false,
        animation: false,
        interaction: {
            mode: 'index',
            intersect: false,
            axis: 'x'
        },
        plugins: {
            legend: {
                position: 'top',
                labels: { color: text, padding: 12, font: { size: 11 } }
            },
            tooltip: {
                enabled: true,
                mode: 'index',
                intersect: false,
                axis: 'x',
                backgroundColor: 'rgba(15, 23, 42, 0.94)',
                titleColor: '#f8fafc',
                bodyColor: '#e2e8f0',
                borderColor: cssVar('--accent'),
                borderWidth: 1,
                padding: 12,
                titleFont: { size: mobile ? 13 : 12, weight: '700' },
                bodyFont: { size: mobile ? 12 : 11 },
                displayColors: true,
                callbacks: {
                    title(items) {
                        return items[0]?.label ?? '';
                    },
                    label(ctx) {
                        const label = ctx.dataset.label || '';
                        return `${label}: ${formatOnlineValue(ctx.parsed.y)}`;
                    }
                }
            }
        },
        onHover(_event, elements, chart) {
            if (!elements.length || !onlineChartMeta) return;
            focusOnlineIndex(elements[0].index, { fromHover: true });
        },
        scales: {
            x: {
                title: { display: true, text: xLabel, color: text, font: { size: 11 } },
                ticks: {
                    color: text,
                    maxRotation: mobile ? 0 : 45,
                    minRotation: mobile ? 0 : 45,
                    font: { size: mobile ? 8 : 9 },
                    autoSkip: true,
                    maxTicksLimit: mobile ? 8 : 20
                },
                grid: { color: grid }
            },
            y: {
                beginAtZero: true,
                title: { display: true, text: 'Игроки', color: text, font: { size: 11 } },
                ticks: { color: text, stepSize: 1, precision: 0, font: { size: 10 } },
                grid: { color: grid }
            }
        },
        elements: isLine ? {
            point: {
                radius: mobile ? 0 : 2,
                hoverRadius: mobile ? 6 : 5,
                hitRadius: mobile ? 28 : 18,
                hoverBorderWidth: 2
            },
            line: {
                borderWidth: mobile ? 2.5 : 2
            }
        } : {
            bar: {
                borderWidth: 1
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

    onlineChartMeta = {
        kind: 'dual',
        labels,
        avgValues,
        maxValues,
        xLabel
    };
    onlineFocusedIndex = -1;

    setupOnlineScrubber(labels);
    const defaultIndex = Math.max(0, labels.length - 1);

    onlineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Средний',
                    data: avgValues,
                    borderColor: cssVar('--accent'),
                    backgroundColor: 'rgba(30, 111, 217, 0.10)',
                    tension: 0.35,
                    fill: true,
                    pointRadius: isCoarsePointer() ? 0 : 2,
                    pointHoverRadius: isCoarsePointer() ? 6 : 5,
                    pointHitRadius: isCoarsePointer() ? 28 : 18,
                    borderWidth: isCoarsePointer() ? 2.5 : 2
                },
                {
                    label: 'Максимум',
                    data: maxValues,
                    borderColor: cssVar('--accent-2'),
                    backgroundColor: 'rgba(11, 167, 180, 0.08)',
                    tension: 0.35,
                    fill: false,
                    pointRadius: isCoarsePointer() ? 0 : 2,
                    pointHoverRadius: isCoarsePointer() ? 6 : 5,
                    pointHitRadius: isCoarsePointer() ? 28 : 18,
                    borderWidth: isCoarsePointer() ? 2.5 : 2
                }
            ]
        },
        options: buildChartOptions(xLabel, true)
    });

    attachOnlineChartInteraction(canvas);
    focusOnlineIndex(defaultIndex, { force: true });
}

function destroyOnlineChart() {
    if (onlineChart) {
        onlineChart.destroy();
        onlineChart = null;
        isInitialized = false;
        onlineChartMeta = null;
    }
}

window.addEventListener('themechange', () => {
    if (isInitialized) switchOnlineMode(currentOnlineMode);
});
