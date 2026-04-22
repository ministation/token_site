const API_BASE = '';

async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE}/api/me`);
        const data = await res.json();
        
        if (data.authenticated) {
            document.getElementById('loginBtn').style.display = 'none';
            document.getElementById('userPanel').style.display = 'flex';
            document.getElementById('userName').textContent = data.username;
            
            if (data.player) {
                // Привязан игровой аккаунт
                document.getElementById('linkSection').style.display = 'none';
                document.getElementById('balanceSection').style.display = 'block';
                loadBalance();
            } else {
                // Не привязан
                document.getElementById('linkSection').style.display = 'block';
                document.getElementById('balanceSection').style.display = 'none';
            }
        } else {
            document.getElementById('loginBtn').style.display = 'block';
            document.getElementById('userPanel').style.display = 'none';
            document.getElementById('linkSection').style.display = 'none';
            document.getElementById('balanceSection').style.display = 'none';
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }
}

function login() {
    window.location.href = `${API_BASE}/login`;
}

function logout() {
    window.location.href = `${API_BASE}/logout`;
}

async function linkPlayer() {
    const uuid = document.getElementById('uuidInput').value.trim();
    const resultDiv = document.getElementById('linkResult');
    if (!uuid) {
        resultDiv.innerHTML = '<p class="error">Введите UUID</p>';
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/link_player`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_uuid: uuid})
        });
        const data = await res.json();
        if (res.ok) {
            resultDiv.innerHTML = '<p class="success">Аккаунт привязан!</p>';
            setTimeout(() => location.reload(), 1500);
        } else {
            resultDiv.innerHTML = `<p class="error">${data.detail}</p>`;
        }
    } catch (e) {
        resultDiv.innerHTML = '<p class="error">Ошибка соединения</p>';
    }
}

async function loadBalance() {
    try {
        const res = await fetch(`${API_BASE}/api/balance`);
        const data = await res.json();
        document.getElementById('balanceDisplay').innerHTML = `
            <p style="font-size: 1.5rem;">${data.nickname}: <strong>${data.balance}</strong> 🪙</p>
        `;
    } catch (e) {}
}

// Инициализация
checkAuth();