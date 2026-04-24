document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM loaded, starting init...');
    
    await checkAuth();
    console.log('Auth done, user:', currentUser);
    
    setupNavigation();
    setupAutocomplete();
    
    // Топ и статистика для всех
    loadTop();
    loadStats();
    
    if (currentUser?.authenticated) {
        if (currentUser.player) {
            currentPlayerId = currentUser.player.player_id;
            console.log('Loading balance for player:', currentPlayerId);
            
            // Загружаем баланс с небольшой задержкой (чтобы DOM точно был готов)
            setTimeout(() => {
                loadMyBalance();
                loadMyDeposits();
                loadMyLoans();
            }, 500);
            
            loadFeed();
        }
        loadChat();
        setInterval(loadChat, 5000);
    } else {
        console.log('Not authenticated, skipping balance');
    }
});