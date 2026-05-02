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
                loadFeed();
                loadServerStatus();
            } else if (section === 'economy') {
                // Загружаем все данные экономики
                if (typeof loadMyBalance === 'function') loadMyBalance();
                if (typeof loadMyDeposits === 'function') loadMyDeposits();
                if (typeof loadMyLoans === 'function') loadMyLoans();
                if (typeof loadTop === 'function') loadTop();
                if (typeof loadStats === 'function') loadStats();
            } else if (section === 'search') {
                document.getElementById('socialSearchInput').value = '';
                if (typeof searchSocial === 'function') {
                    searchSocial('');
                }
            } else if (section === 'messages') {
                if (typeof loadDialogs === 'function') {
                    loadDialogs();
                }
            } else if (section === 'bans') {
                if (typeof loadBans === 'function') {
                    loadBans();
                }
            } else if (section === 'online') {
                setTimeout(() => {
                    if (typeof initOnlineChart === 'function') {
                        initOnlineChart();
                    }
                }, 300);
            } else {
                if (typeof destroyOnlineChart === 'function') {
                    destroyOnlineChart();
                }
            }
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(sectionId + 'Section');
    if (target) target.classList.add('active');
}