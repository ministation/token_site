const SLOT_SYMBOLS = ['cherry', 'lemon', 'orange', 'grapes', 'diamond', 'seven'];
let slotInterval = null;

// Автодополнение
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
                    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(e.target.value)}`);
                    const players = await res.json();
                    document.getElementById('playersList').innerHTML = players.map(p => `<option value="${p}">`).join('');
                }, 300);
            });
        }
    });
}

// Баланс
async function loadMyBalance() {
    try {
        const data = await apiCall('GET', '/api/balance');
        document.getElementById('myBalance').innerHTML = `<p>Баланс: <strong>${data.balance}</strong> ${COIN_ICON}</p>`;
    } catch (e) {}
}

async function checkBalance() {
    const nick = document.getElementById('balanceNick').value;
    const resultDiv = document.getElementById('balanceResult');
    if (!nick) { resultDiv.innerHTML = '<p class="error">Введите ник</p>'; return; }
    try {
        const data = await apiCall('GET', `/api/balance/${encodeURIComponent(nick)}`);
        resultDiv.innerHTML = `<p>${data.nickname}: <strong>${data.balance}</strong> ${COIN_ICON}</p>`;
    } catch (e) {
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

async function transfer() {
    const receiver = document.getElementById('receiverNick').value;
    const amount = parseInt(document.getElementById('transferAmount').value);
    const resultDiv = document.getElementById('transferResult');
    if (!receiver || !amount) { resultDiv.innerHTML = '<p class="error">Заполните все поля</p>'; return; }
    if (amount < 1) { resultDiv.innerHTML = '<p class="error">Сумма >= 1</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/transfer', { receiver_nick: receiver, amount });
        resultDiv.innerHTML = `<p class="success">✅ Переведено ${data.amount} ${COIN_ICON} игроку ${data.receiver}. Ваш баланс: ${data.new_balance} ${COIN_ICON}</p>`;
        loadMyBalance(); loadTop();
    } catch (e) { resultDiv.innerHTML = `<p class="error">${e.message}</p>`; }
}

// Слоты
function startSlotAnimation() {
    const slotMachine = document.getElementById('slotMachine');
    const slotResult = document.getElementById('slotResult');
    if (slotMachine) slotMachine.style.display = 'flex';
    if (slotResult) slotResult.innerHTML = '🎲 Крутим...';
    
    document.querySelectorAll('.slot-reel').forEach(r => r.classList.add('slot-spinning'));
    
    let spins = 0;
    slotInterval = setInterval(() => {
        const slot1 = document.getElementById('slot1');
        const slot2 = document.getElementById('slot2');
        const slot3 = document.getElementById('slot3');
        if (slot1) slot1.innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
        if (slot2) slot2.innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
        if (slot3) slot3.innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
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
    if (prize >= 15) symbols = ['diamond', 'diamond', 'diamond'];
    else if (prize >= 8) symbols = ['seven', 'seven', 'cherry'];
    else if (prize >= 4) symbols = ['grapes', 'grapes', 'lemon'];
    else symbols = ['cherry', 'lemon', 'orange'];
    
    const slot1 = document.getElementById('slot1');
    const slot2 = document.getElementById('slot2');
    const slot3 = document.getElementById('slot3');
    if (slot1) slot1.innerHTML = `<img src="/static/slots/${symbols[0]}.png" alt="">`;
    if (slot2) slot2.innerHTML = `<img src="/static/slots/${symbols[1]}.png" alt="">`;
    if (slot3) slot3.innerHTML = `<img src="/static/slots/${symbols[2]}.png" alt="">`;
    
    const slotResult = document.getElementById('slotResult');
    if (slotResult) slotResult.innerHTML = prize >= 15 ? `🎉 ДЖЕКПОТ! ${prize} ${COIN_ICON}` : `✨ Выигрыш: ${prize} ${COIN_ICON}`;
}

async function playLottery() {
    const resultDiv = document.getElementById('lotteryResult');
    startSlotAnimation();
    try {
        const data = await apiCall('POST', '/api/lottery');
        setTimeout(() => {
            stopSlotAnimation(data.prize);
            if (resultDiv) resultDiv.innerHTML = `<p class="success">🎉 Выигрыш: ${data.prize} ${COIN_ICON}! Новый баланс: ${data.new_balance} ${COIN_ICON}</p>`;
            loadMyBalance(); loadTop();
        }, 1500);
    } catch (e) {
        clearInterval(slotInterval);
        const slotMachine = document.getElementById('slotMachine');
        if (slotMachine) slotMachine.style.display = 'none';
        if (resultDiv) resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

// Банк
function showBankTab(tab) {
    document.querySelectorAll('.bank-tab').forEach(t => t.style.display = 'none');
    const tabEl = document.getElementById(tab + 'Tab');
    if (tabEl) tabEl.style.display = 'block';
    document.querySelectorAll('#bankSection .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
}

async function createDeposit() {
    const amount = parseInt(document.getElementById('depositAmount').value);
    const resultDiv = document.getElementById('depositResult');
    if (!amount || amount < 10) { resultDiv.innerHTML = '<p class="error">Минимальная сумма: 10</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/deposit', { amount });
        resultDiv.innerHTML = `<p class="success">✅ Вклад создан! ID: ${data.deposit_id}</p>`;
        loadMyBalance(); loadMyDeposits();
    } catch (e) { resultDiv.innerHTML = `<p class="error">${e.message}</p>`; }
}

async function loadMyDeposits() {
    try {
        const deposits = await apiCall('GET', '/api/deposits');
        document.getElementById('withdrawSelect').innerHTML = deposits.map(d => 
            `<option value="${d.deposit_id}">ID ${d.deposit_id}: ${d.amount} → ${d.total} (${new Date(d.mature_at).toLocaleDateString()})</option>`
        ).join('');
    } catch (e) {}
}

async function withdrawDeposit() {
    const depositId = document.getElementById('withdrawSelect').value;
    if (!depositId) return;
    try {
        const data = await apiCall('POST', '/api/withdraw', { deposit_id: parseInt(depositId) });
        document.getElementById('withdrawResult').innerHTML = `<p class="success">✅ Получено ${data.amount} ${COIN_ICON}</p>`;
        loadMyBalance(); loadMyDeposits();
    } catch (e) { document.getElementById('withdrawResult').innerHTML = `<p class="error">${e.message}</p>`; }
}

async function loadMyLoans() {
    try {
        const loans = await apiCall('GET', '/api/loans');
        document.getElementById('repaySelect').innerHTML = loans.map(l => 
            `<option value="${l.loan_id}">ID ${l.loan_id}: долг ${l.remaining}/${l.total} (${new Date(l.due_at).toLocaleDateString()})</option>`
        ).join('');
    } catch (e) {}
}

async function createLoan() {
    const amount = parseInt(document.getElementById('loanAmount').value);
    if (!amount || amount <= 0) { document.getElementById('loanResult').innerHTML = '<p class="error">Введите сумму</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/loan', { amount });
        document.getElementById('loanResult').innerHTML = `<p class="success">✅ Заём выдан! ID: ${data.loan_id}</p>`;
        loadMyBalance(); loadMyLoans();
    } catch (e) { document.getElementById('loanResult').innerHTML = `<p class="error">${e.message}</p>`; }
}

async function repayLoan() {
    const loanId = parseInt(document.getElementById('repaySelect').value);
    const amount = document.getElementById('repayAmount').value;
    if (!loanId) return;
    try {
        const body = { loan_id: loanId };
        if (amount) body.amount = parseInt(amount);
        const data = await apiCall('POST', '/api/repay', body);
        document.getElementById('repayResult').innerHTML = `<p class="success">✅ ${data.message}</p>`;
        loadMyBalance(); loadMyLoans();
    } catch (e) { document.getElementById('repayResult').innerHTML = `<p class="error">${e.message}</p>`; }
}

async function loadTop() {
    try {
        const data = await apiCall('GET', '/api/top');
        let html = '';
        data.players.forEach((p, i) => html += `<div class="top-player">${i+1}. ${p.name} — ${p.balance} ${COIN_ICON}</div>`);
        html += `<div class="stats-grid" style="margin-top:15px">
            <div class="stat-item"><div class="stat-value">${data.stats.total_players}</div><div class="stat-label">Игроков</div></div>
            <div class="stat-item"><div class="stat-value">${data.stats.total_tokens}</div><div class="stat-label">Монет</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.total_deposits}</div><div class="stat-label">Вкладов</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.total_loans}</div><div class="stat-label">Займов</div></div>
        </div>`;
        document.getElementById('topResult').innerHTML = html;
    } catch (e) {}
}

async function loadStats() {
    try {
        const data = await apiCall('GET', '/api/stats');
        document.getElementById('statsResult').innerHTML = `<div class="stats-grid">
            <div class="stat-item"><div class="stat-value">${data.stats.total_players}</div><div class="stat-label">Игроков</div></div>
            <div class="stat-item"><div class="stat-value">${data.stats.total_tokens}</div><div class="stat-label">Монет</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.total_deposits}</div><div class="stat-label">Вкладов</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.total_loans}</div><div class="stat-label">Займов</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.liquidity}</div><div class="stat-label">Свободно</div></div>
        </div>`;
    } catch (e) {}
}