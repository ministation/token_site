document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    setupNavigation();
    setupAutocomplete();
    
    loadTop();
    loadStats();
    
    if (currentUser?.authenticated) {
        if (currentUser.player) {
            currentPlayerId = currentUser.player.player_id;
            
            setTimeout(() => {
                if (typeof loadMyBalance === 'function') loadMyBalance();
                if (typeof loadMyDeposits === 'function') loadMyDeposits();
                if (typeof loadMyLoans === 'function') loadMyLoans();
            }, 500);
            
            if (typeof loadFeed === 'function') loadFeed();
        }
        if (typeof loadChat === 'function') {
            loadChat();
            setInterval(loadChat, 5000);
        }
    }
});