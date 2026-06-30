function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const section = btn.dataset.section;
            showSection(section);
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (section === 'profile') {
                if (currentUser?.player) {
                    loadMyProfile();
                } else {
                    alert('Привяжите Discord к игровому аккаунту');
                }
            } else if (section === 'home') {
                if (typeof loadFeed === 'function') loadFeed();
                if (typeof loadServerStatus === 'function') loadServerStatus();
            } else if (section === 'economy') {
                if (typeof loadMyBalance === 'function') loadMyBalance();
                if (typeof loadMyDeposits === 'function') loadMyDeposits();
                if (typeof loadMyLoans === 'function') loadMyLoans();
                if (typeof loadTop === 'function') loadTop();
                if (typeof loadStats === 'function') loadStats();
            } else if (section === 'bans') {
                if (typeof loadBans === 'function') loadBans();
            } else if (section === 'online') {
                if (typeof initOnlineChart === 'function') initOnlineChart();
            } else if (section === 'search') {
                const input = document.getElementById('socialSearchInput');
                if (input) input.value = '';
                if (typeof searchSocial === 'function') searchSocial('');
            } else if (section === 'messages') {
                if (typeof loadDialogs === 'function') loadDialogs();
            }
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(sectionId + 'Section');
    if (target) target.classList.add('active');
}
