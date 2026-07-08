let compensationState = null;
let compensationTimerId = null;

function formatCompensationCountdown(totalSeconds) {
    const sec = Math.max(0, totalSeconds | 0);
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
}

function hideCompensationCard() {
    const card = document.getElementById('compensationCard');
    if (card) card.hidden = true;
    if (compensationTimerId) {
        clearInterval(compensationTimerId);
        compensationTimerId = null;
    }
    compensationState = null;
}

function updateCompensationTimer() {
    if (!compensationState?.active) {
        hideCompensationCard();
        return;
    }
    const remaining = Math.max(
        0,
        Math.floor((compensationState.ends_ts * 1000 - Date.now()) / 1000)
    );
    const timerEl = document.getElementById('compensationTimer');
    if (timerEl) timerEl.textContent = formatCompensationCountdown(remaining);
    if (remaining <= 0) {
        hideCompensationCard();
        return;
    }
    compensationState.remaining_seconds = remaining;
}

function renderCompensationCard() {
    const card = document.getElementById('compensationCard');
    const amountEl = document.getElementById('compensationAmount');
    const btn = document.getElementById('compensationCollectBtn');
    const resultEl = document.getElementById('compensationResult');
    if (!card || !compensationState?.active) {
        hideCompensationCard();
        return;
    }

    card.hidden = false;
    if (amountEl) amountEl.textContent = compensationState.amount;
    updateCompensationTimer();

    if (!btn) return;

    if (!currentUser?.authenticated) {
        btn.disabled = false;
        btn.textContent = 'Войти и собрать';
        if (resultEl) resultEl.innerHTML = '<p class="compensation-note">Нужен вход через Discord</p>';
        return;
    }

    if (!currentUser?.player) {
        btn.disabled = true;
        btn.textContent = 'Собрать компенсацию';
        if (resultEl) {
            resultEl.innerHTML = '<p class="compensation-note">Привяжите игровой аккаунт к Discord</p>';
        }
        return;
    }

    if (compensationState.claimed) {
        btn.disabled = true;
        btn.textContent = 'Компенсация получена';
        if (resultEl) resultEl.innerHTML = '<p class="success">Вы уже забрали компенсацию</p>';
        return;
    }

    btn.disabled = false;
    btn.textContent = 'Собрать компенсацию';
    if (resultEl) resultEl.innerHTML = '';
}

async function loadCompensation() {
    try {
        const data = await apiCall('GET', '/api/compensation/active');
        if (!data.active) {
            hideCompensationCard();
            return;
        }
        compensationState = data;
        compensationState.ends_ts = Math.floor(Date.now() / 1000) + (data.remaining_seconds || 0);
        renderCompensationCard();
        if (compensationTimerId) clearInterval(compensationTimerId);
        compensationTimerId = setInterval(updateCompensationTimer, 1000);
    } catch (e) {
        hideCompensationCard();
    }
}

async function claimCompensation() {
    const btn = document.getElementById('compensationCollectBtn');
    const resultEl = document.getElementById('compensationResult');
    if (!compensationState?.active) return;

    if (!currentUser?.authenticated) {
        login();
        return;
    }
    if (!currentUser?.player) {
        if (resultEl) {
            resultEl.innerHTML = '<p class="error">Игровой аккаунт не привязан к Discord</p>';
        }
        return;
    }

    if (btn) btn.disabled = true;
    try {
        const data = await apiCall('POST', '/api/compensation/claim');
        compensationState.claimed = true;
        if (resultEl) {
            resultEl.innerHTML = `<p class="success">Получено ${data.amount} ${COIN_ICON}. Баланс: ${data.new_balance} ${COIN_ICON}</p>`;
        }
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Компенсация получена';
        }
        if (typeof refreshBalance === 'function') refreshBalance();
    } catch (e) {
        if (btn) btn.disabled = false;
        if (resultEl) resultEl.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
        await loadCompensation();
    }
}

function initCompensation() {
    loadCompensation();
    setInterval(loadCompensation, 60000);
}

document.addEventListener('DOMContentLoaded', initCompensation);
