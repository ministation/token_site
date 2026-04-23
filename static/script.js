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