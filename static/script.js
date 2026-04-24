document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    setupNavigation();
    
    if (currentUser?.authenticated) {
        if (currentUser.player) {
            currentPlayerId = currentUser.player.player_id;
            loadMyBalance();
            loadMyDeposits();
            loadMyLoans();
            loadFeed();
        }
        loadChat();
        setInterval(loadChat, 5000);
        loadTop();
        loadStats();
    }
    
    setupAutocomplete();
});

async function loadServerStatus() {
    try {
        const res = await fetch('/api/server-status');
        const data = await res.json();
        
        const dot = document.getElementById('statusDot');
        dot.className = 'status-dot' + (data.online ? ' online' : '');
        
        document.getElementById('statusName').textContent = data.name;
        document.getElementById('statusPlayers').textContent = data.players;
        document.getElementById('statusMax').textContent = data.max_players;
        document.getElementById('statusMap').textContent = data.map;
        document.getElementById('statusPreset').textContent = data.preset || '-';
        
        const percent = Math.min(100, (data.players / data.max_players) * 100);
        document.getElementById('progressFill').style.width = percent + '%';
    } catch (e) {
        console.error('Status error:', e);
    }
}

// В DOMContentLoaded добавь:
loadServerStatus();
setInterval(loadServerStatus, 30000); // обновление каждые 30 сек