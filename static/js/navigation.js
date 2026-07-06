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

            if (section === 'home') {
                if (typeof loadFeed === 'function') loadFeed();
                if (typeof loadServerStatus === 'function') loadServerStatus();
            } else if (section === 'chat') {
                if (typeof initGlobalChat === 'function') initGlobalChat();
            } else if (section === 'messages') {
                if (!currentUser?.authenticated) {
                    alert('Войдите через Discord, чтобы писать сообщения');
                    return;
                }
                if (typeof setupPmUserSearch === 'function') setupPmUserSearch();
                if (typeof loadDialogs === 'function') loadDialogs();
                if (typeof startPmPolling === 'function') startPmPolling();
            } else if (section === 'inventory') {
                if (!currentUser?.authenticated) {
                    alert('Войдите через Discord, чтобы видеть инвентарь');
                    return;
                }
                if (typeof loadInventory === 'function') loadInventory();
            } else if (section === 'economy') {
                if (typeof loadMyBalance === 'function') loadMyBalance();
                if (typeof loadMyDeposits === 'function') loadMyDeposits();
                if (typeof loadMyLoans === 'function') loadMyLoans();
                if (typeof loadTop === 'function') loadTop();
                if (typeof loadStats === 'function') loadStats();
            } else if (section === 'bans') {
                if (typeof loadBans === 'function') loadBans();
            } else if (section === 'online') {
                if (typeof initStatsSection === 'function') initStatsSection();
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
    if (sectionId !== 'messages' && typeof stopPmPolling === 'function') stopPmPolling();
    if (sectionId !== 'chat' && typeof stopGlobalChatPolling === 'function') stopGlobalChatPolling();
}
