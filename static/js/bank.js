const SLOT_SYMBOLS = [
    '/static/icons/%D0%B1%D1%83%D1%81%D1%82%20%D1%83%D0%BD%D0%B0%D1%82%D0%B8.png',
    '/static/icons/%D0%BA%D0%BE%D1%81%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9%20%D1%83%D0%BD%D0%B0%D1%82%D0%B8.png',
    '/static/icons/%D0%B7%D0%BE%D0%BB%D0%BE%D1%82%D0%BE%D0%B9%20%D1%83%D0%BD%D0%B0%D1%82%D0%B8.png',
    '/static/icons/%D0%BC%D0%B0%D0%B3%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9%20%D1%83%D0%BD%D0%B0%D1%82%D0%B8.png',
    '/static/icons/%D0%B3%D0%B8%D0%B3%D0%B0%20%D1%83%D0%BD%D0%B0%D1%82%D0%B8.png',
];
let slotInterval = null;
let audioCtx = null;

function getAudioCtx() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
}

function playTone(freq, duration, type = 'square', volume = 0.08) {
    try {
        const ctx = getAudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = type;
        osc.frequency.value = freq;
        gain.gain.value = volume;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
        osc.stop(ctx.currentTime + duration);
    } catch (e) {}
}

function playSpinTick() {
    playTone(180 + Math.random() * 80, 0.05, 'square', 0.04);
}

function playWinSound(prize) {
    if (prize >= 15) {
        [523, 659, 784, 1047].forEach((f, i) => setTimeout(() => playTone(f, 0.2, 'sine', 0.12), i * 120));
    } else if (prize >= 8) {
        [440, 554, 659].forEach((f, i) => setTimeout(() => playTone(f, 0.15, 'sine', 0.1), i * 100));
    } else {
        playTone(330, 0.12, 'sine', 0.08);
        setTimeout(() => playTone(440, 0.15, 'sine', 0.08), 100);
    }
}

function playLoseSound() {
    playTone(150, 0.2, 'sawtooth', 0.05);
    setTimeout(() => playTone(100, 0.25, 'sawtooth', 0.04), 150);
}

function setupAutocomplete() {
    const inputs = ['balanceNick', 'receiverNick'];
    let searchTimeout;
    inputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('input', async (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(async () => {
                    if (e.target.value.length < 2) return;
                    const res = await fetch('/api/search?q=' + encodeURIComponent(e.target.value));
                    const players = await res.json();
                    const list = document.getElementById('playersList');
                    if (list) list.innerHTML = players.map(p => `<option value="${p}">`).join('');
                }, 300);
            });
        }
    });
}

async function loadMyBalance() {
    try {
        const res = await fetch('/api/balance');
        if (!res.ok) return;
        const data = await res.json();
        const el = document.getElementById('myBalance');
        if (el) el.innerHTML = `<p>Баланс: <strong>${data.balance}</strong> ${COIN_ICON}</p>`;
    } catch (e) {}
}

async function checkBalance() {
    const nick = document.getElementById('balanceNick')?.value;
    const resultDiv = document.getElementById('balanceResult');
    if (!resultDiv) return;
    if (!nick) { resultDiv.innerHTML = '<p class="error">Введите ник</p>'; return; }
    try {
        const data = await apiCall('GET', `/api/balance/${encodeURIComponent(nick)}`);
        resultDiv.innerHTML = `<p>${escapeHtml(data.nickname)}: <strong>${data.balance}</strong> ${COIN_ICON}</p>`;
    } catch (e) {
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

async function transfer() {
    const receiver = document.getElementById('receiverNick')?.value;
    const amount = parseInt(document.getElementById('transferAmount')?.value);
    const resultDiv = document.getElementById('transferResult');
    if (!resultDiv) return;
    if (!receiver || !amount) { resultDiv.innerHTML = '<p class="error">Заполните все поля</p>'; return; }
    if (amount < 1) { resultDiv.innerHTML = '<p class="error">Сумма >= 1</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/transfer', { receiver_nick: receiver, amount });
        resultDiv.innerHTML = `<p class="success">Переведено ${data.amount} ${COIN_ICON} игроку ${escapeHtml(data.receiver)}. Ваш баланс: ${data.new_balance} ${COIN_ICON}</p>`;
        loadMyBalance();
        loadTop();
    } catch (e) {
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

function startSlotAnimation() {
    const slotMachine = document.getElementById('slotMachine');
    const slotResult = document.getElementById('slotResult');
    if (!slotMachine || !slotResult) return;
    slotMachine.style.display = 'flex';
    slotResult.innerHTML = 'Крутим...';
    document.querySelectorAll('.slot-reel').forEach(r => r.classList.add('slot-spinning'));
    let spins = 0;
    slotInterval = setInterval(() => {
        ['slot1', 'slot2', 'slot3'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                const sym = SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)];
                el.innerHTML = `<img src="${sym}" alt="">`;
            }
        });
        playSpinTick();
        spins++;
        if (spins >= 15) {
            clearInterval(slotInterval);
            document.querySelectorAll('.slot-reel').forEach(r => r.classList.remove('slot-spinning'));
        }
    }, 100);
}

function stopSlotAnimation(prize) {
    if (slotInterval) { clearInterval(slotInterval); slotInterval = null; }
    document.querySelectorAll('.slot-reel').forEach(r => r.classList.remove('slot-spinning'));
    let symbols;
    if (prize >= 15) symbols = [SLOT_SYMBOLS[4], SLOT_SYMBOLS[4], SLOT_SYMBOLS[4]];
    else if (prize >= 8) symbols = [SLOT_SYMBOLS[3], SLOT_SYMBOLS[3], SLOT_SYMBOLS[1]];
    else if (prize >= 4) symbols = [SLOT_SYMBOLS[2], SLOT_SYMBOLS[2], SLOT_SYMBOLS[0]];
    else symbols = [SLOT_SYMBOLS[0], SLOT_SYMBOLS[1], SLOT_SYMBOLS[0]];
    ['slot1', 'slot2', 'slot3'].forEach((id, i) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = `<img src="${symbols[i]}" alt="">`;
    });
    const slotResult = document.getElementById('slotResult');
    if (slotResult) {
        slotResult.innerHTML = prize >= 15
            ? `🎉 ДЖЕКПОТ! ${prize} ${COIN_ICON}`
            : prize > 0 ? `Выигрыш: ${prize} ${COIN_ICON}` : 'Не повезло...';
    }
    if (prize > 0) playWinSound(prize);
    else playLoseSound();
}

async function playLottery() {
    const resultDiv = document.getElementById('lotteryResult');
    if (!resultDiv) return;
    try { const ctx = getAudioCtx(); if (ctx.state === 'suspended') await ctx.resume(); } catch (e) {}
    startSlotAnimation();
    try {
        const data = await apiCall('POST', '/api/lottery');
        setTimeout(() => {
            stopSlotAnimation(data.prize);
            resultDiv.innerHTML = `<p class="success">Выигрыш: ${data.prize} ${COIN_ICON}! Новый баланс: ${data.new_balance} ${COIN_ICON}</p>`;
            loadMyBalance();
            loadTop();
        }, 1500);
    } catch (e) {
        clearInterval(slotInterval);
        const slotMachine = document.getElementById('slotMachine');
        if (slotMachine) slotMachine.style.display = 'none';
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

async function loadTop() {
    try {
        const data = await apiCall('GET', '/api/top');
        const container = document.getElementById('topResult');
        if (!container) return;
        if (!data.players?.length) {
            container.innerHTML = '<p class="empty-state">Пока нет данных</p>';
            return;
        }
        container.innerHTML = data.players.map((p, i) =>
            `<div class="top-player">
                <span class="rank">${i + 1}</span>
                <span class="name">${escapeHtml(p.name)}</span>
                <span class="balance">${p.balance} ${COIN_ICON}</span>
            </div>`
        ).join('');
    } catch (e) {
        const container = document.getElementById('topResult');
        if (container) container.innerHTML = '<p class="error">Не удалось загрузить</p>';
    }
}

async function loadStats() {
    try {
        const data = await apiCall('GET', '/api/stats');
        const container = document.getElementById('statsResult');
        if (!container) return;
        const s = data.stats || {};
        const b = data.bank || {};
        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${s.total_players ?? 0}</div>
                    <div class="stat-label">Игроков</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${s.total_tokens ?? 0}</div>
                    <div class="stat-label">Монет в обороте</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${b.total_deposits ?? 0}</div>
                    <div class="stat-label">Во вкладах</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${b.total_loans ?? 0}</div>
                    <div class="stat-label">В займах</div>
                </div>
            </div>`;
    } catch (e) {
        const container = document.getElementById('statsResult');
        if (container) container.innerHTML = '<p class="error">Не удалось загрузить</p>';
    }
}

function showEconomyTab(tab, btn) {
    document.querySelectorAll('.economy-tab-content').forEach(t => t.style.display = 'none');
    const tabMap = { wallet: 'economyWallet', bank: 'economyBank', lottery: 'economyLottery' };
    const targetId = tabMap[tab];
    if (targetId) {
        const target = document.getElementById(targetId);
        if (target) target.style.display = 'block';
    }
    document.querySelectorAll('.economy-tabs .tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'wallet') {
        loadMyBalance();
        loadTop();
        loadStats();
    } else if (tab === 'bank') {
        loadMyDeposits();
        loadMyLoans();
    }
}

function showBankSubTab(tab, btn) {
    document.querySelectorAll('.bank-tab').forEach(t => t.style.display = 'none');
    const target = document.getElementById(tab + 'Tab');
    if (target) target.style.display = 'block';
    document.querySelectorAll('#economyBank .tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'withdraw') loadMyDeposits();
    if (tab === 'repay') loadMyLoans();
}

async function createDeposit() {
    const amount = parseInt(document.getElementById('depositAmount')?.value);
    const resultDiv = document.getElementById('depositResult');
    if (!resultDiv) return;
    if (isNaN(amount)) { resultDiv.innerHTML = '<p class="error">Введите сумму</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/deposit', { amount });
        resultDiv.innerHTML = `<p class="success">Вклад создан. ID: ${data.deposit_id}</p>`;
        loadMyDeposits();
        loadMyBalance();
    } catch (e) {
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

async function loadMyDeposits() {
    const select = document.getElementById('withdrawSelect');
    if (!select) return;
    select.innerHTML = '<option value="">— выберите вклад —</option>';
    try {
        const deposits = await apiCall('GET', '/api/deposits');
        deposits.forEach(d => {
            const option = document.createElement('option');
            option.value = d.deposit_id;
            option.textContent = `ID ${d.deposit_id}: ${d.amount} → ${d.total}`;
            select.appendChild(option);
        });
    } catch (e) {}
}

async function withdrawDeposit() {
    const id = document.getElementById('withdrawSelect')?.value;
    const resultDiv = document.getElementById('withdrawResult');
    if (!resultDiv) return;
    if (!id) { resultDiv.innerHTML = '<p class="error">Выберите вклад</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/withdraw', { deposit_id: parseInt(id) });
        resultDiv.innerHTML = `<p class="success">Снято ${data.amount} монет.</p>`;
        loadMyDeposits();
        loadMyBalance();
    } catch (e) {
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

async function createLoan() {
    const amount = parseInt(document.getElementById('loanAmount')?.value);
    const resultDiv = document.getElementById('loanResult');
    if (!resultDiv) return;
    if (isNaN(amount)) { resultDiv.innerHTML = '<p class="error">Введите сумму</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/loan', { amount });
        resultDiv.innerHTML = `<p class="success">Заём получен. ID: ${data.loan_id}</p>`;
        loadMyLoans();
        loadMyBalance();
    } catch (e) {
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

async function loadMyLoans() {
    const select = document.getElementById('repaySelect');
    if (!select) return;
    select.innerHTML = '<option value="">— выберите заём —</option>';
    try {
        const loans = await apiCall('GET', '/api/loans');
        loans.forEach(l => {
            const option = document.createElement('option');
            option.value = l.loan_id;
            option.textContent = `ID ${l.loan_id}: ${l.remaining}/${l.total}`;
            select.appendChild(option);
        });
    } catch (e) {}
}

async function repayLoan() {
    const id = document.getElementById('repaySelect')?.value;
    const resultDiv = document.getElementById('repayResult');
    if (!resultDiv) return;
    if (!id) { resultDiv.innerHTML = '<p class="error">Выберите заём</p>'; return; }
    const amountStr = document.getElementById('repayAmount')?.value;
    const body = { loan_id: parseInt(id) };
    if (amountStr) body.amount = parseInt(amountStr);
    try {
        const data = await apiCall('POST', '/api/repay', body);
        resultDiv.innerHTML = `<p class="success">${data.message}</p>`;
        loadMyLoans();
        loadMyBalance();
    } catch (e) {
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

function refreshBalance() {
    loadMyBalance();
}
