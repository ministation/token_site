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
            if (!canAccessSection(section, { navClick: true })) return;
            navigateTo(section);
            closeMobileNav();
        });
    });

    window.addEventListener('hashchange', handleHashRoute);
    if (!location.hash) {
        location.hash = '#/home';
    } else {
        handleHashRoute();
    }
}

function canAccessSection(section, opts = {}) {
    if (section === 'messages' && !currentUser?.authenticated) {
        alert('Войдите через Discord, чтобы писать сообщения');
        return false;
    }
    if (section === 'inventory') {
        if (opts.playerId) return true;
        if (!currentUser?.authenticated) {
            alert('Войдите через Discord');
            return false;
        }
    }
    if (section === 'admin' && !currentUser?.is_admin && !currentUser?.is_time_keeper && !currentUser?.is_moderator) {
        alert('Доступ только для администраторов и staff');
        return false;
    }
    return true;
}

function navigateTo(path) {
    const route = String(path || 'home').replace(/^#\/?/, '');
    const next = route.startsWith('#') ? route : `#/${route}`;
    if (location.hash === next) {
        handleHashRoute();
    } else {
        location.hash = next;
    }
}

function parseHashRoute() {
    const raw = (location.hash || '#/home').replace(/^#\/?/, '');
    const pathOnly = raw.split('?')[0];
    const parts = pathOnly.split('/').filter(Boolean);
    const head = parts[0] || 'home';
    if (head === 'player' && parts[1]) {
        return { section: 'inventory', playerId: decodeURIComponent(parts[1].split('?')[0]) };
    }
    return { section: head, playerId: null };
}

function handleHashRoute() {
    const { section, playerId } = parseHashRoute();
    if (section === 'donate') {
        const q = (location.hash.split('?')[1] || '');
        location.replace('/donate' + (q ? `?${q}` : ''));
        return;
    }
    if (!canAccessSection(section, { playerId })) {
        location.hash = '#/home';
        return;
    }

    showSection(section);
    document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.section === section);
    });

    if (section === 'inventory') {
        const id = playerId || currentUser?.social_id || currentPlayerId;
        if (id && typeof loadProfile === 'function') loadProfile(id);
        else if (typeof loadMyProfile === 'function') loadMyProfile();
    } else {
        runSectionInit(section);
    }

    if (section !== 'messages' && typeof pollNotifications === 'function') {
        pollNotifications();
    }

    const titles = {
        home: 'Главная',
        chat: 'Чат',
        messages: 'Сообщения',
        inventory: playerId ? 'Профиль' : 'Профиль',
        economy: 'Монетки',
        bans: 'Наказания',
        online: 'Статистика',
        admin: 'Админ',
        privacy: 'Политика конфиденциальности',
        terms: 'Пользовательское соглашение',
        pricing: 'Цены и тарифы',
        support: 'Обращения',
    };
    document.title = `${titles[section] || 'Страница'} — Мини-станция`;
}

function runSectionInit(section, playerId = null) {
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
        const id = playerId || currentUser?.social_id || currentPlayerId;
        if (id && typeof loadProfile === 'function') loadProfile(id);
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
        if (typeof configureAdminTabsForUser === 'function') configureAdminTabsForUser();
        if (currentUser?.is_admin && typeof loadAdminStats === 'function') loadAdminStats();
        else if (currentUser?.is_moderator && typeof showAdminTab === 'function') {
            const gameBtn = document.querySelector('.admin-tabs .tab[data-mod-ok][onclick*="game"]');
            showAdminTab('game', gameBtn);
        } else if (currentUser?.is_time_keeper && typeof showAdminTab === 'function') {
            const playtimeBtn = document.querySelector('.admin-tabs .tab[data-staff-only]');
            showAdminTab('playtime', playtimeBtn);
        }
    } else if (section === 'support') {
        if (typeof initSupportSection === 'function') initSupportSection();
    }
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
    document.body.classList.toggle('section-chat', sectionId === 'chat');
    document.body.classList.toggle('section-messages', sectionId === 'messages');
    if (sectionId === 'chat' || sectionId === 'messages') {
        requestAnimationFrame(() => {
            syncPanelHeightToSidebar(sectionId);
            requestAnimationFrame(() => syncPanelHeightToSidebar(sectionId));
        });
    }
    if (sectionId !== 'messages' && typeof stopPmPolling === 'function') stopPmPolling();
    if (sectionId !== 'chat' && typeof stopGlobalChatPolling === 'function') stopGlobalChatPolling();
    if (sectionId !== 'chat' && typeof stopChatUsersPolling === 'function') stopChatUsersPolling();
}

function syncPanelHeightToSidebar(sectionId) {
    const shell = sectionId === 'messages'
        ? document.querySelector('#messagesSection .dc-shell')
        : document.querySelector('#chatSection .dc-shell');
    if (!shell) return;

    const topbar = document.querySelector('.topbar');
    const topbarH = topbar ? Math.ceil(topbar.getBoundingClientRect().height) : 64;
    document.documentElement.style.setProperty('--chat-topbar', `${topbarH}px`);

    // Сбрасываем, чтобы измерить реальное положение под шапкой/паддингами
    shell.style.height = '';
    shell.style.maxHeight = '';
    shell.style.minHeight = '0';

    requestAnimationFrame(() => {
        const top = Math.ceil(shell.getBoundingClientRect().top);
        const bottomPad = 8;
        const h = Math.max(280, Math.floor(window.innerHeight - top - bottomPad));
        shell.style.height = `${h}px`;
        shell.style.maxHeight = `${h}px`;
        shell.style.minHeight = '0';
    });
}

window.addEventListener('resize', () => {
    if (document.body.classList.contains('section-chat')) syncPanelHeightToSidebar('chat');
    else if (document.body.classList.contains('section-messages')) syncPanelHeightToSidebar('messages');
});
