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

function showEconomyTab(tab) {
    // Скрываем все вкладки экономики
    document.querySelectorAll('.economy-tab-content').forEach(t => t.style.display = 'none');
    
    // Показываем нужную
    const tabMap = {
        'wallet': 'economyWallet',
        'bank': 'economyBank',
        'lottery': 'economyLottery'
    };
    const targetId = tabMap[tab];
    if (targetId) {
        document.getElementById(targetId).style.display = 'block';
    }
    
    // Обновляем активный класс на кнопках
    document.querySelectorAll('.economy-tabs .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    
    // Загружаем данные для конкретной вкладки
    if (tab === 'wallet') {
        if (typeof loadMyBalance === 'function') loadMyBalance();
        if (typeof loadTop === 'function') loadTop();
        if (typeof loadStats === 'function') loadStats();
    } else if (tab === 'bank') {
        if (typeof loadMyDeposits === 'function') loadMyDeposits();
        if (typeof loadMyLoans === 'function') loadMyLoans();
    }
}

function showBankSubTab(tab) {
    document.querySelectorAll('.bank-tab').forEach(t => t.style.display = 'none');
    const target = document.getElementById(tab + 'Tab');
    if (target) target.style.display = 'block';
    
    document.querySelectorAll('#economyBank .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
}

// Загружаем условия вкладов и список активных вкладов при открытии
document.addEventListener('DOMContentLoaded', () => {
  loadDepositTiers();
  loadActiveDeposits(); // для заполнения выпадающего списка
  loadActiveLoans();    // для заполнения выпадающего списка займов
});

// Переключение вкладок
function showBankTab(tabName) {
  document.querySelectorAll('.bank-tab').forEach(tab => tab.style.display = 'none');
  document.querySelectorAll('.tab').forEach(btn => btn.classList.remove('active'));
  document.getElementById(tabName + 'Tab').style.display = 'block';
  event.target.classList.add('active');
  if (tabName === 'withdraw') loadActiveDeposits();
  if (tabName === 'repay') loadActiveLoans();
}

// Загрузка таблицы условий вкладов
async function loadDepositTiers() {
  try {
    const resp = await fetch('/api/deposits');
    const data = await resp.json();
    const tiers = data.limits.tiers;
    let html = '';
    tiers.forEach(tier => {
      const min = tier.min;
      const max = tier.max;
      const days = tier.days;
      const payoutMin = Math.floor(min * 1.2);  // +20%
      const payoutMax = Math.floor(max * 1.2);
      html += `<tr>
        <td>${min}–${max}</td>
        <td>${days} дн.</td>
        <td>+20%</td>
        <td>${payoutMin}–${payoutMax}</td>
      </tr>`;
    });
    document.getElementById('depositTiersBody').innerHTML = html;
  } catch (e) {
    console.error('Ошибка загрузки условий вкладов:', e);
  }
}

// Создание вклада
async function createDeposit() {
  const amount = parseInt(document.getElementById('depositAmount').value);
  if (isNaN(amount)) return alert('Введите сумму');
  try {
    const resp = await fetch('/api/deposit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ amount })
    });
    const data = await resp.json();
    if (data.success) {
      document.getElementById('depositResult').innerHTML =
        `<p>Вклад создан. ID: ${data.deposit_id}, срок: ${data.duration_days} дн., к получению: ${data.total} монет.</p>`;
      loadActiveDeposits();
      refreshBalance(); // если есть функция обновления баланса
    } else {
      document.getElementById('depositResult').innerHTML = `<p class="error">${data.detail || 'Ошибка'}</p>`;
    }
  } catch (e) {
    console.error(e);
  }
}

// Загрузка активных вкладов в выпадающий список
async function loadActiveDeposits() {
  const select = document.getElementById('withdrawSelect');
  select.innerHTML = '<option value="">— выберите вклад —</option>';
  try {
    const resp = await fetch('/api/deposits');
    const data = await resp.json();
    data.deposits.forEach(d => {
      const option = document.createElement('option');
      option.value = d.deposit_id;
      option.textContent = `ID ${d.deposit_id}: ${d.amount} монет → ${d.total} (выплата ${d.mature_date})`;
      select.appendChild(option);
    });
  } catch (e) {
    console.error(e);
  }
}

// Снятие вклада
async function withdrawDeposit() {
  const id = document.getElementById('withdrawSelect').value;
  if (!id) return alert('Выберите вклад');
  try {
    const resp = await fetch('/api/withdraw', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ deposit_id: parseInt(id) })
    });
    const data = await resp.json();
    if (data.success) {
      document.getElementById('withdrawResult').innerHTML =
        `<p>Снято ${data.amount} монет.</p>`;
      loadActiveDeposits();
      refreshBalance();
    } else {
      document.getElementById('withdrawResult').innerHTML = `<p class="error">${data.detail || 'Ошибка'}</p>`;
    }
  } catch (e) {
    console.error(e);
  }
}

// Займы – создание
async function createLoan() {
  const amount = parseInt(document.getElementById('loanAmount').value);
  if (isNaN(amount)) return alert('Введите сумму');
  try {
    const resp = await fetch('/api/loan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ amount })
    });
    const data = await resp.json();
    if (data.success) {
      document.getElementById('loanResult').innerHTML =
        `<p>Заём получен. ID: ${data.loan_id}, вернуть: ${data.total} монет до ${new Date(data.due_at).toLocaleDateString()}</p>`;
      loadActiveLoans();
      refreshBalance();
    } else {
      document.getElementById('loanResult').innerHTML = `<p class="error">${data.detail || 'Ошибка'}</p>`;
    }
  } catch (e) {
    console.error(e);
  }
}

// Загрузка активных займов в выпадающий список
async function loadActiveLoans() {
  const select = document.getElementById('repaySelect');
  select.innerHTML = '<option value="">— выберите заём —</option>';
  try {
    const resp = await fetch('/api/loans');
    const loans = await resp.json();
    loans.forEach(l => {
      const option = document.createElement('option');
      option.value = l.loan_id;
      option.textContent = `ID ${l.loan_id}: осталось ${l.remaining} из ${l.total} (срок ${l.due_at})`;
      select.appendChild(option);
    });
  } catch (e) {
    console.error(e);
  }
}

// Погашение займа
async function repayLoan() {
  const id = document.getElementById('repaySelect').value;
  if (!id) return alert('Выберите заём');
  const amountStr = document.getElementById('repayAmount').value;
  const body = { loan_id: parseInt(id) };
  if (amountStr) body.amount = parseInt(amountStr);
  try {
    const resp = await fetch('/api/repay', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    const data = await resp.json();
    if (data.success) {
      document.getElementById('repayResult').innerHTML =
        `<p>${data.message}</p>`;
      loadActiveLoans();
      refreshBalance();
    } else {
      document.getElementById('repayResult').innerHTML = `<p class="error">${data.detail || 'Ошибка'}</p>`;
    }
  } catch (e) {
    console.error(e);
  }
}

// Заглушка обновления баланса (замените на вашу реальную функцию)
function refreshBalance() {
  if (typeof loadBalance === 'function') loadBalance();
}