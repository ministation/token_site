const SLOT_SYMBOLS = ['cherry', 'lemon', 'orange', 'grapes', 'diamond', 'seven'];
let slotInterval = null;

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
                    document.getElementById('playersList').innerHTML = players.map(p => `<option value="${p}">`).join('');
                }, 300);
            });
        }
    });
}

async function loadMyBalance() {
    try {
        const res = await fetch('/api/balance');
        if (!res.ok) throw new Error('Not authenticated');
        const data = await res.json();
        const el = document.getElementById('myBalance');
        if (el) el.innerHTML = '<p>Баланс: <strong>' + data.balance + '</strong> ' + COIN_ICON + '</p>';
    } catch (e) { console.log('Balance:', e.message); }
}

async function checkBalance() {
    const nick = document.getElementById('balanceNick').value;
    const resultDiv = document.getElementById('balanceResult');
    if (!nick) { resultDiv.innerHTML = '<p class="error">Введите ник</p>'; return; }
    try {
        const res = await fetch('/api/balance/' + encodeURIComponent(nick));
        if (!res.ok) throw new Error('Not found');
        const data = await res.json();
        resultDiv.innerHTML = '<p>' + data.nickname + ': <strong>' + data.balance + '</strong> ' + COIN_ICON + '</p>';
    } catch (e) { resultDiv.innerHTML = '<p class="error">' + e.message + '</p>'; }
}

async function transfer() {
    const receiver = document.getElementById('receiverNick').value;
    const amount = parseInt(document.getElementById('transferAmount').value);
    const resultDiv = document.getElementById('transferResult');
    if (!receiver || !amount) { resultDiv.innerHTML = '<p class="error">Заполните поля</p>'; return; }
    try {
        const res = await fetch('/api/transfer', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ receiver_nick: receiver, amount })
        });
        if (!res.ok) { const err = await res.json(); throw new Error(err.detail); }
        const data = await res.json();
        resultDiv.innerHTML = '<p class="success">✅ ' + data.amount + ' ' + COIN_ICON + ' игроку ' + data.receiver + '</p>';
        loadMyBalance(); loadTop();
    } catch (e) { resultDiv.innerHTML = '<p class="error">' + e.message + '</p>'; }
}

async function loadTop() {
    try {
        const res = await fetch('/api/top');
        const data = await res.json();
        let html = '';
        data.players.forEach((p, i) => html += '<div class="top-player">' + (i+1) + '. ' + p.name + ' — ' + p.balance + ' ' + COIN_ICON + '</div>');
        document.getElementById('topResult').innerHTML = html;
    } catch (e) {}
}

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('statsResult').innerHTML = '<p>Игроков: ' + data.stats.total_players + ' | Монет: ' + data.stats.total_tokens + '</p>';
    } catch (e) {}
}