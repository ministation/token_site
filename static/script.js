document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    setupNavigation();
    setupAutocomplete();

    loadTop();
    loadStats();
    loadFeed();

    if (currentUser?.authenticated) {
        if (currentUser.player) {
            currentPlayerId = currentUser.player.player_id;
            setTimeout(() => {
                if (typeof loadMyBalance === 'function') loadMyBalance();
                if (typeof loadMyDeposits === 'function') loadMyDeposits();
                if (typeof loadMyLoans === 'function') loadMyLoans();
            }, 500);
        }

        const openPm = sessionStorage.getItem('openPm');
        if (openPm) {
            sessionStorage.removeItem('openPm');
            try {
                const { playerId, nickname } = JSON.parse(openPm);
                showSection('messages');
                document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
                const btn = document.querySelector('.nav-btn[data-section="messages"]');
                if (btn) btn.classList.add('active');
                if (typeof setupPmUserSearch === 'function') setupPmUserSearch();
                if (typeof startPmPolling === 'function') startPmPolling();
                if (typeof openConversation === 'function') openConversation(playerId, nickname);
            } catch (e) {}
        }
    }
});
