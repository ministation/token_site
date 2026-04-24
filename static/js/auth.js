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
        } else {
            document.getElementById('loginBtn').style.display = 'block';
            document.getElementById('userPanel').style.display = 'none';
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }
}

function login() { window.location.href = `${API_BASE}/login`; }
function logout() { window.location.href = `${API_BASE}/logout`; }