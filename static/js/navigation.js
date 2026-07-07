function setupNavigation() {
    const navToggle = document.getElementById('navToggle');
    const mainNav = document.getElementById('mainNav');
    const navBackdrop = document.getElementById('navBackdrop');

    function setNavOpen(open) {
        if (mainNav) mainNav.classList.toggle('open', open);
        if (navToggle) navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (navBackdrop) {
            navBackdrop.classList.toggle('visible', open);
            navBackdrop.setAttribute('aria-hidden', open ? 'false' : 'true');
        }
        document.body.classList.toggle('nav-open', open);
    }

    if (navToggle && mainNav) {
        navToggle.addEventListener('click', () => {
            setNavOpen(!mainNav.classList.contains('open'));
        });
    }

    if (navBackdrop) {
        navBackdrop.addEventListener('click', () => setNavOpen(false));
    }

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const section = btn.dataset.section;

            if (section === 'messages' && !currentUser?.authenticated) {
                alert('Войдите через Discord, чтобы писать сообщения');
                return;
            }
            if (section === 'inventory' && !currentUser?.authenticated) {
                alert('Войдите через Discord, чтобы видеть инвентарь');
                return;
            }

            showSection(section);
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            closeMobileNav();

            if (section === 'home') {
                if (typeof loadFeed === 'function') loadFeed();
                if (typeof loadServerStatus === 'function') loadServerStatus();
                if (typeof markAllFeedSeen === 'function') markAllFeedSeen();
            } else if (section === 'chat') {
                if (typeof initGlobalChat === 'function') initGlobalChat();
                if (typeof loadChatUsers === 'function') loadChatUsers('');
            } else if (section === 'messages') {
                if (typeof setupPmUserSearch === 'function') setupPmUserSearch();
                if (typeof loadDialogs === 'function') loadDialogs();
                if (typeof startPmPolling === 'function') startPmPolling();
                if (typeof pollNotifications === 'function') pollNotifications();
            } else if (section === 'inventory') {
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
            } else if (section === 'admin') {
                if (!currentUser?.is_admin) {
                    alert('Доступ только для администраторов');
                    return;
                }
                if (typeof loadAdminStats === 'function') loadAdminStats();
            } else if (section === 'moderator') {
                if (!currentUser?.is_moderator) {
                    alert('Доступ только для модерации');
                    return;
                }
                if (typeof loadModeratorAppeals === 'function') loadModeratorAppeals();
            }

            if (section !== 'messages' && typeof pollNotifications === 'function') {
                pollNotifications();
            }
        });
    });
}

function closeMobileNav() {
    const mainNav = document.getElementById('mainNav');
    const navToggle = document.getElementById('navToggle');
    const navBackdrop = document.getElementById('navBackdrop');
    if (mainNav) mainNav.classList.remove('open');
    if (navToggle) navToggle.setAttribute('aria-expanded', 'false');
    if (navBackdrop) {
        navBackdrop.classList.remove('visible');
        navBackdrop.setAttribute('aria-hidden', 'true');
    }
    document.body.classList.remove('nav-open');
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(sectionId + 'Section');
    if (target) target.classList.add('active');
    if (sectionId !== 'messages' && typeof stopPmPolling === 'function') stopPmPolling();
    if (sectionId !== 'chat' && typeof stopGlobalChatPolling === 'function') stopGlobalChatPolling();
}
