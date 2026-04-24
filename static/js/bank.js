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
        if (!res.ok) return;
        const data = await res.json();
        const el = document.getElementById('myBalance');
        if (el) el.innerHTML = '<p>Баланс: <strong>' + data.balance + '</strong> ' + COIN_ICON + '</p>';
    } catch (e) {}
}

async function loadMyDeposits() {
    try {
        const res = await fetch('/api/deposits');
        const deposits = await res.json();
        const sel = document.getElementById('withdrawSelect');
        if (sel) sel.innerHTML = deposits.map(d => '<option value="' + d.deposit_id + '">ID ' + d.deposit_id + ': ' + d.amount + ' → ' + d.total + '</option>').join('');
    } catch (e) {}
}

async function loadMyLoans() {
    try {
        const res = await fetch('/api/loans');
        const loans = await res.json();
        const sel = document.getElementById('repaySelect');
        if (sel) sel.innerHTML = loans.map(l => '<option value="' + l.loan_id + '">ID ' + l.loan_id + ': ' + l.remaining + '/' + l.total + '</option>').join('');
    } catch (e) {}
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