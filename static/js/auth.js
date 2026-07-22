function staffBadgeHtml(user) {
    if (user?.is_admin) return ' <span class="admin-badge">ADMIN</span>';
    if (user?.is_moderator) return ' <span class="mod-badge">MOD</span>';
    let html = '';
    if (user?.is_content_maker) html += ' <span class="content-maker-badge">КОНТЕНТ</span>';
    if (user?.is_time_keeper) html += ' <span class="time-keeper-badge">ХРАНИТЕЛЬ</span>';
    return html;
}

async function checkAuth() {
    try {
        if (new URLSearchParams(location.search).get('site_banned') === '1') {
            history.replaceState({}, '', location.pathname + location.hash);
            alert('Доступ к сайту заблокирован. Обратитесь к администрации.');
        }
        const res = await fetch(`${API_BASE}/api/me`);
        const data = await res.json();
        currentUser = data;

        if (data.site_banned) {
            document.getElementById('loginBtn').style.display = '';
            document.getElementById('userPanel').style.display = 'none';
            updateAuthUI();
            const reason = data.ban_reason || 'Нарушение правил';
            alert(`Доступ к сайту заблокирован.\n${reason}`);
            return;
        }

        if (data.authenticated) {
            document.getElementById('loginBtn').style.display = 'none';
            const panel = document.getElementById('userPanel');
            panel.style.display = 'flex';
            panel.innerHTML = `
                ${typeof chatAvatarHtml === 'function'
                    ? chatAvatarHtml(data.avatar, 'user-panel-avatar', data.presence || 'offline')
                    : (data.avatar ? `<img src="${data.avatar}" alt="" onerror="this.style.display='none'">` : '')}
                <span id="userName">${data.display_name || data.username}${staffBadgeHtml(data)}</span>
                <button type="button" onclick="openMyProfile()" title="Мой профиль"><i class="fa-solid fa-user"></i></button>
                <button type="button" onclick="logout()">Выйти</button>
            `;
            if (data.player) {
                currentPlayerId = data.player.player_id;
            }
            if (data.social_id) {
                currentUser.social_id = data.social_id;
            }
            updateAuthUI();
            if (typeof initAdminPanel === 'function') initAdminPanel();
            if (typeof refreshAdminRatingIfVisible === 'function') refreshAdminRatingIfVisible();
            if (typeof startNotificationPolling === 'function') startNotificationPolling();
            if (typeof loadCompensation === 'function') loadCompensation();
        } else {
            document.getElementById('loginBtn').style.display = '';
            document.getElementById('userPanel').style.display = 'none';
            updateAuthUI();
            if (typeof refreshAdminRatingIfVisible === 'function') refreshAdminRatingIfVisible();
            if (typeof stopNotificationPolling === 'function') stopNotificationPolling();
            if (typeof loadCompensation === 'function') loadCompensation();
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }
}

function updateAuthUI() {
    const postCard = document.getElementById('createPostCard');
    const toolbar = document.getElementById('feedToolbar');
    const canPostHere = currentUser?.authenticated
        && (typeof currentForumCategory === 'undefined'
            || currentForumCategory !== 'news'
            || currentUser?.is_admin);
    if (toolbar) toolbar.hidden = !canPostHere;
    if (postCard && !canPostHere) {
        postCard.hidden = true;
        postCard.style.display = 'none';
    }
    if (typeof updateFeedCreateBtn === 'function') updateFeedCreateBtn();
    if (typeof updateForumStaffOptions === 'function') updateForumStaffOptions();
    if (typeof syncPostFormWithForum === 'function') syncPostFormWithForum();
    const chatInput = document.getElementById('globalChatInputArea');
    const chatHint = document.getElementById('globalChatLoginHint');
    if (chatInput) chatInput.style.display = currentUser?.authenticated ? 'flex' : 'none';
    if (chatHint) chatHint.style.display = currentUser?.authenticated ? 'none' : 'block';
    const profileNav = document.getElementById('profileNavBtn');
    if (profileNav) profileNav.style.display = currentUser?.authenticated ? '' : 'none';
}

async function solvePowChallenge(challenge) {
    const nonce = String(challenge.nonce || '');
    const difficulty = Number(challenge.difficulty) || 3;
    const prefix = '0'.repeat(difficulty);
    // sha256 via SubtleCrypto
    for (let counter = 0; counter < 5_000_000; counter++) {
        const raw = `${nonce}:${counter}`;
        const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
        const hex = [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
        if (hex.startsWith(prefix)) return String(counter);
        if (counter > 0 && counter % 25000 === 0) {
            await new Promise(r => setTimeout(r, 0));
        }
    }
    throw new Error('Не удалось пройти антибот-проверку');
}

async function login() {
    try {
        const chRes = await fetch(`${API_BASE}/api/auth/challenge`);
        if (!chRes.ok) {
            const err = await chRes.json().catch(() => ({}));
            throw new Error(err.detail || 'Антибот недоступен');
        }
        const challenge = await chRes.json();
        const counter = await solvePowChallenge(challenge);
        const params = new URLSearchParams({
            n: challenge.nonce,
            e: String(challenge.exp),
            d: String(challenge.difficulty),
            s: challenge.sig,
            c: counter,
        });
        window.location.href = `${API_BASE}/login?${params.toString()}`;
    } catch (e) {
        alert(e.message || 'Не удалось войти');
    }
}
function logout() { window.location.href = `${API_BASE}/logout`; }
