function setupNavigation() {
    const navToggle = document.getElementById('navToggle');
    const mainNav = document.getElementById('mainNav');

    if (navToggle && mainNav) {
        navToggle.addEventListener('click', () => {
            const open = mainNav.classList.toggle('open');
            navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
    }

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const section = btn.dataset.section;
            showSection(section);
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            closeMobileNav();

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
                if (!currentUser?.player) {
                    alert('Войдите и привяжите Discord к игровому аккаунту');
                    return;
                }
                if (typeof setupPmUserSearch === 'function') setupPmUserSearch();
                if (typeof loadDialogs === 'function') loadDialogs();
            }
        });
    });
}

function closeMobileNav() {
    const mainNav = document.getElementById('mainNav');
    const navToggle = document.getElementById('navToggle');
    if (mainNav) mainNav.classList.remove('open');
    if (navToggle) navToggle.setAttribute('aria-expanded', 'false');
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(sectionId + 'Section');
    if (target) target.classList.add('active');
}
