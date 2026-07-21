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
        const res = await fetch(`${API_BASE}/api/me`);
        const data = await res.json();
        currentUser = data;

        if (data.authenticated) {
            document.getElementById('loginBtn').style.display = 'none';
            const panel = document.getElementById('userPanel');
            panel.style.display = 'flex';
            panel.innerHTML = `
                ${data.avatar ? `<img src="${data.avatar}" alt="" onerror="this.style.display='none'">` : ''}
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
    if (postCard) {
        const canPostHere = currentUser?.authenticated
            && (typeof currentForumCategory === 'undefined'
                || currentForumCategory !== 'news'
                || currentUser?.is_admin);
        postCard.style.display = canPostHere ? 'block' : 'none';
    }
    if (typeof updateForumStaffOptions === 'function') updateForumStaffOptions();
    if (typeof syncPostFormWithForum === 'function') syncPostFormWithForum();
    const chatInput = document.getElementById('globalChatInputArea');
    const chatHint = document.getElementById('globalChatLoginHint');
    if (chatInput) chatInput.style.display = currentUser?.authenticated ? 'flex' : 'none';
    if (chatHint) chatHint.style.display = currentUser?.authenticated ? 'none' : 'block';
    const profileNav = document.getElementById('profileNavBtn');
    if (profileNav) profileNav.style.display = currentUser?.authenticated ? '' : 'none';
}

function login() { window.location.href = `${API_BASE}/login`; }
function logout() { window.location.href = `${API_BASE}/logout`; }
