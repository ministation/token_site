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
    slotMachine.style.display = 'flex';
    slotResult.innerHTML = '🎲 Крутим...';
    
    document.querySelectorAll('.slot-reel').forEach(r => r.classList.add('slot-spinning'));
    
    let spins = 0;
    slotInterval = setInterval(() => {
        document.getElementById('slot1').innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
        document.getElementById('slot2').innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
        document.getElementById('slot3').innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
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
    
    document.getElementById('slot1').innerHTML = `<img src="/static/slots/${symbols[0]}.png" alt="">`;
    document.getElementById('slot2').innerHTML = `<img src="/static/slots/${symbols[1]}.png" alt="">`;
    document.getElementById('slot3').innerHTML = `<img src="/static/slots/${symbols[2]}.png" alt="">`;
    
    document.getElementById('slotResult').innerHTML = prize >= 15 ? `🎉 ДЖЕКПОТ! ${prize} ${COIN_ICON}` : `✨ Выигрыш: ${prize} ${COIN_ICON}`;
}

async function playLottery() {
    const resultDiv = document.getElementById('lotteryResult');
    startSlotAnimation();
    try {
        const data = await apiCall('POST', '/api/lottery');
        setTimeout(() => {
            stopSlotAnimation(data.prize);
            resultDiv.innerHTML = `<p class="success">🎉 Выигрыш: ${data.prize} ${COIN_ICON}! Новый баланс: ${data.new_balance} ${COIN_ICON}</p>`;
            loadMyBalance(); loadTop();
        }, 1500);
    } catch (e) {
        clearInterval(slotInterval);
        document.getElementById('slotMachine').style.display = 'none';
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

// Банк
function showBankTab(tab) {
    document.querySelectorAll('.bank-tab').forEach(t => t.style.display = 'none');
    document.getElementById(tab + 'Tab').style.display = 'block';
    document.querySelectorAll('#bankSection .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
}

async function createDeposit() { /* без изменений */ }
async function loadMyDeposits() { /* без изменений */ }
async function withdrawDeposit() { /* без изменений */ }
async function loadMyLoans() { /* без изменений */ }
async function createLoan() { /* без изменений */ }
async function repayLoan() { /* без изменений */ }
async function loadTop() { /* без изменений */ }
async function loadStats() { /* без изменений */ }