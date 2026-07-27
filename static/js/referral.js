const REFERRAL_AUTH_ONCE_KEY = 'ms_auth_once';
let pendingAuthProvider = null;
let referralModalMode = 'postauth';

function hasAuthenticatedBefore() {
    try {
        return localStorage.getItem(REFERRAL_AUTH_ONCE_KEY) === '1';
    } catch (e) {
        return false;
    }
}

function markAuthenticatedOnce() {
    try {
        localStorage.setItem(REFERRAL_AUTH_ONCE_KEY, '1');
    } catch (e) {}
}

function getStoredReferralCode() {
    const params = new URLSearchParams(location.search);
    const fromUrl = (params.get('ref') || '').trim().toUpperCase();
    if (fromUrl) {
        sessionStorage.setItem('pendingReferralCode', fromUrl);
        return fromUrl;
    }
    return (sessionStorage.getItem('pendingReferralCode') || '').trim().toUpperCase();
}

function shouldShowPreAuthReferralGate() {
    if (hasAuthenticatedBefore()) return false;
    const params = new URLSearchParams(location.search);
    if (params.get('ref')) return false;
    return true;
}

function requestLogin(provider) {
    pendingAuthProvider = provider;
    if (!shouldShowPreAuthReferralGate()) {
        proceedLogin(provider);
        return;
    }
    showPreAuthReferralModal(provider);
}

function proceedLogin(provider) {
    if (provider === 'ss14') {
        if (typeof loginSs14Direct === 'function') loginSs14Direct();
        else window.location.href = `${API_BASE || ''}/login/ss14`;
        return;
    }
    if (typeof loginDirect === 'function') loginDirect();
}

function providerLabel(provider) {
    return provider === 'ss14' ? 'SS14' : 'Discord';
}

function updateReferralModalMode(mode, provider) {
    referralModalMode = mode;
    const modal = document.getElementById('referralModal');
    if (modal) modal.dataset.mode = mode;

    const title = document.getElementById('referralModalTitle');
    const desc = document.getElementById('referralModalDesc');
    const primaryBtn = document.getElementById('referralPrimaryBtn');
    const skipBtn = document.getElementById('referralSkipBtn');

    if (mode === 'preauth') {
        if (title) title.innerHTML = '<i class="fa-solid fa-gift"></i> Реферальный код';
        if (desc) {
            desc.innerHTML = 'При первой регистрации можно указать код друга и получить <b>3 монеты</b>. Друг получит <b>5 монет</b>. Поле необязательное.';
        }
        if (primaryBtn) primaryBtn.textContent = `Продолжить через ${providerLabel(provider)}`;
        if (skipBtn) skipBtn.textContent = 'Пропустить и войти';
        return;
    }

    if (title) title.innerHTML = '<i class="fa-solid fa-gift"></i> Добро пожаловать!';
    if (desc) {
        desc.innerHTML = 'Есть реферальный код друга? Введите его и получите <b>3 монеты</b>. Друг получит <b>5 монет</b>.';
    }
    if (primaryBtn) primaryBtn.textContent = 'Применить';
    if (skipBtn) skipBtn.textContent = 'Пропустить';
}

function showPreAuthReferralModal(provider) {
    pendingAuthProvider = provider;
    const modal = document.getElementById('referralModal');
    if (!modal) {
        proceedLogin(provider);
        return;
    }
    updateReferralModalMode('preauth', provider);
    const input = document.getElementById('referralCodeInput');
    const result = document.getElementById('referralApplyResult');
    if (input) input.value = '';
    if (result) result.textContent = '';
    modal.hidden = false;
    document.body.classList.add('modal-open');
    input?.focus();
}

function referralModalPrimaryClick() {
    if (referralModalMode === 'preauth') confirmPreAuthReferral();
    else submitReferralCode();
}

function referralModalSkipClick() {
    if (referralModalMode === 'preauth') skipPreAuthReferral();
    else skipReferralPrompt();
}

function confirmPreAuthReferral() {
    const input = document.getElementById('referralCodeInput');
    const code = (input?.value || '').trim().toUpperCase();
    if (code) sessionStorage.setItem('pendingReferralCode', code);
    else sessionStorage.removeItem('pendingReferralCode');
    hideReferralModal();
    const provider = pendingAuthProvider || 'discord';
    pendingAuthProvider = null;
    proceedLogin(provider);
}

function skipPreAuthReferral() {
    sessionStorage.removeItem('pendingReferralCode');
    hideReferralModal();
    const provider = pendingAuthProvider || 'discord';
    pendingAuthProvider = null;
    proceedLogin(provider);
}

function referralInviteUrl(code) {
    const base = (typeof API_BASE !== 'undefined' ? API_BASE : '') || '';
    const origin = base || window.location.origin;
    return `${origin}/?ref=${encodeURIComponent(code)}`;
}

async function copyReferralLink(code) {
    const url = referralInviteUrl(code);
    try {
        await navigator.clipboard.writeText(url);
        alert('Ссылка скопирована');
    } catch (e) {
        prompt('Скопируйте ссылку:', url);
    }
}

async function copyReferralCode(code) {
    try {
        await navigator.clipboard.writeText(code);
        alert('Код скопирован');
    } catch (e) {
        prompt('Скопируйте код:', code);
    }
}

function showReferralModal() {
    updateReferralModalMode('postauth');
    const modal = document.getElementById('referralModal');
    if (!modal) return;
    const input = document.getElementById('referralCodeInput');
    const stored = getStoredReferralCode();
    if (input && stored) input.value = stored;
    modal.hidden = false;
    document.body.classList.add('modal-open');
}

function hideReferralModal() {
    const modal = document.getElementById('referralModal');
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove('modal-open');
}

async function submitReferralCode() {
    const input = document.getElementById('referralCodeInput');
    const result = document.getElementById('referralApplyResult');
    const code = (input?.value || '').trim();
    if (!code) {
        if (result) result.textContent = 'Введите код';
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/referral/apply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || 'Не удалось применить код');
        if (result) result.textContent = data.message || 'Готово!';
        sessionStorage.removeItem('pendingReferralCode');
        setTimeout(() => {
            hideReferralModal();
            if (typeof checkAuth === 'function') checkAuth();
        }, 900);
    } catch (e) {
        if (result) result.textContent = e.message || 'Ошибка';
    }
}

async function skipReferralPrompt() {
    try {
        await fetch(`${API_BASE}/api/referral/skip`, { method: 'POST' });
    } catch (e) {}
    sessionStorage.removeItem('pendingReferralCode');
    hideReferralModal();
}

function maybeShowReferralWelcome() {
    const params = new URLSearchParams(location.search);
    if (params.get('welcome') === '1' || params.get('ref')) {
        history.replaceState({}, '', location.pathname + location.hash);
    }
    if (params.get('welcome') === '1' && currentUser?.authenticated) {
        if (currentUser.referral?.needs_prompt) {
            showReferralModal();
        }
    }
    if (params.get('ss14_linked') === '1') {
        history.replaceState({}, '', location.pathname + location.hash);
        alert('Игровой аккаунт SS14 успешно привязан!');
        if (typeof checkAuth === 'function') checkAuth();
    }
    const ss14Err = params.get('ss14_link_error');
    if (ss14Err) {
        history.replaceState({}, '', location.pathname + location.hash);
        const messages = {
            oauth_config: 'Ошибка настройки SS14 OAuth. Проверьте Client ID, Secret и callback URL в .env и в кабинете SS14.',
            redirect_uri: 'Неверный callback URL. В OAuth-приложении SS14 должен быть указан: https://ministation.ru/api/ss14/callback',
            access_denied: 'Авторизация SS14 отменена.',
        };
        alert(messages[ss14Err] || `Не удалось войти через SS14: ${decodeURIComponent(ss14Err)}`);
    }
}

function renderReferralCard(info) {
    if (!info?.code) return '';
    const url = referralInviteUrl(info.code);
    return `
        <div class="referral-card">
            <h3><i class="fa-solid fa-user-group"></i> Реферальная программа</h3>
            <p class="referral-hint">Пригласите друга — вы получите <b>${info.referrer_reward || 5}</b> монет, друг — <b>${info.referee_reward || 3}</b>.</p>
            <div class="referral-code-row">
                <span class="referral-code">${escapeHtml(info.code)}</span>
                <button type="button" class="btn-sm" onclick='copyReferralCode(${JSON.stringify(info.code)})'>
                    <i class="fa-solid fa-copy"></i> Код
                </button>
                <button type="button" class="btn-sm" onclick='copyReferralLink(${JSON.stringify(info.code)})'>
                    <i class="fa-solid fa-link"></i> Ссылка
                </button>
            </div>
            <p class="referral-meta">Приглашено: ${info.referrals_count || 0}</p>
            ${info.referred_by ? `<p class="referral-meta">Вы пришли по коду: <b>${escapeHtml(info.referred_by)}</b></p>` : ''}
            <p class="referral-link-preview">${escapeHtml(url)}</p>
        </div>
    `;
}

function renderGameLinkCard(linked, ss14Enabled, hasDiscord) {
    if (linked) {
        const extra = hasDiscord === false
            ? '<p class="game-link-note">Вы вошли через SS14. Discord можно привязать в игре.</p>'
            : '';
        return `
            <div class="game-link-card game-link-card--ok">
                <h3><i class="fa-solid fa-link"></i> Игровой аккаунт</h3>
                <p>SS14 привязан. Монетки и донат доступны.</p>
                ${extra}
            </div>
        `;
    }
    if (!ss14Enabled) {
        return `
            <div class="game-link-card">
                <h3><i class="fa-solid fa-link"></i> Привязка аккаунта</h3>
                <p>Зайдите в игру и нажмите «Привязать Discord» в лобби или меню ESC.</p>
            </div>
        `;
    }
    if (hasDiscord === false) {
        return `
            <div class="game-link-card game-link-card--ok">
                <h3><img src="/static/ss14-logo.png" alt="SS14" class="login-ss14-logo" width="52" height="22"> Вход через SS14</h3>
                <p>Вы авторизованы через аккаунт Wizard Den.</p>
            </div>
        `;
    }
    return `
        <div class="game-link-card">
            <h3><img src="/static/ss14-logo.png" alt="SS14" class="login-ss14-logo" width="52" height="22"> Привязать SS14</h3>
            <p>Войдите через аккаунт Wizard Den, чтобы связать профиль с игрой.</p>
            <button type="button" class="btn-sm game-link-btn" onclick="startSs14Link()">
                <img src="/static/ss14-logo.png" alt="SS14" class="login-ss14-logo" width="48" height="20">
                Авторизоваться через SS14
            </button>
        </div>
    `;
}

function startSs14Link() {
    window.location.href = `${API_BASE}/api/ss14/link`;
}

async function refreshLinkStatus() {
    const hosts = [
        document.getElementById('gameLinkCard'),
        document.getElementById('profileGameLinkCard'),
    ].filter(Boolean);
    if (!hosts.length || !currentUser?.authenticated) return;
    try {
        const res = await fetch(`${API_BASE}/api/link/status`);
        const data = await res.json();
        const html = renderGameLinkCard(data.linked, data.ss14_oauth_enabled, data.has_discord);
        hosts.forEach(host => { host.innerHTML = html; });
    } catch (e) {}
}

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('referralCodeInput');
    input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            referralModalPrimaryClick();
        }
    });
});
