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
                <span id="userName">${data.display_name || data.username}</span>
                <button onclick="logout()">Выйти</button>
            `;
            if (data.player) {
                currentPlayerId = data.player.player_id;
            }
            if (data.social_id) {
                currentUser.social_id = data.social_id;
            }
            updateAuthUI();
        } else {
            document.getElementById('loginBtn').style.display = '';
            document.getElementById('userPanel').style.display = 'none';
            updateAuthUI();
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }
}

function updateAuthUI() {
    const postCard = document.getElementById('createPostCard');
    if (postCard) {
        postCard.style.display = currentUser?.authenticated ? 'block' : 'none';
    }
    const chatInput = document.getElementById('globalChatInputArea');
    const chatHint = document.getElementById('globalChatLoginHint');
    if (chatInput) chatInput.style.display = currentUser?.authenticated ? 'flex' : 'none';
    if (chatHint) chatHint.style.display = currentUser?.authenticated ? 'none' : 'block';
}

function login() { window.location.href = `${API_BASE}/login`; }
function logout() { window.location.href = `${API_BASE}/logout`; }
