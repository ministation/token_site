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
        if (dot) {
            dot.className = 'status-dot' + (data.online ? ' online' : '');
        }
        
        const nameEl = document.getElementById('statusName');
        if (nameEl) nameEl.textContent = data.name || 'Мини-станция';
        
        const playersEl = document.getElementById('statusPlayers');
        if (playersEl) playersEl.textContent = data.players || 0;
        
        const maxEl = document.getElementById('statusMax');
        if (maxEl) maxEl.textContent = data.max_players || 100;
        
        const mapEl = document.getElementById('statusMap');
        if (mapEl) mapEl.textContent = data.map || '-';
        
        const presetEl = document.getElementById('statusPreset');
        if (presetEl) presetEl.textContent = data.preset || '-';
        
        const fill = document.getElementById('progressFill');
        if (fill) {
            const percent = Math.min(100, ((data.players || 0) / (data.max_players || 100)) * 100);
            fill.style.width = percent + '%';
        }
    } catch (e) {
        console.error('Status error:', e);
    }
}