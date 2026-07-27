function getStoredReferralCode() {
    const params = new URLSearchParams(location.search);
    const fromUrl = (params.get('ref') || '').trim().toUpperCase();
    if (fromUrl) {
        sessionStorage.setItem('pendingReferralCode', fromUrl);
        return fromUrl;
    }
    return (sessionStorage.getItem('pendingReferralCode') || '').trim().toUpperCase();
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
    const modal = document.getElementById('referralModal');
    if (!modal) return;
    const input = document.getElementById('referralCodeInput');
    const stored = typeof getStoredReferralCode === 'function' ? getStoredReferralCode() : '';
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
        alert(`Не удалось привязать SS14: ${decodeURIComponent(ss14Err)}`);
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

function renderGameLinkCard(linked, ss14Enabled) {
    if (linked) {
        return `
            <div class="game-link-card game-link-card--ok">
                <h3><i class="fa-solid fa-link"></i> Игровой аккаунт</h3>
                <p>Discord привязан к SS14. Монетки и донат доступны.</p>
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
    return `
        <div class="game-link-card">
            <h3><i class="fa-solid fa-rocket"></i> Привязать SS14</h3>
            <p>Войдите через аккаунт Wizard Den, чтобы связать Discord с игровым персонажем.</p>
            <button type="button" class="btn-sm game-link-btn" onclick="startSs14Link()">
                <i class="fa-solid fa-right-to-bracket"></i> Войти через SS14
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
        const html = renderGameLinkCard(data.linked, data.ss14_oauth_enabled);
        hosts.forEach(host => { host.innerHTML = html; });
    } catch (e) {}
}
