let notifyPollInterval = null;
let feedMetaCache = null;
let lastPmUnread = 0;
let feedSeenInitialized = false;

function feedSeenKey(category) {
    return `feedSeen_${category}`;
}

function getFeedSeenId(category) {
    const v = localStorage.getItem(feedSeenKey(category));
    return v ? parseInt(v, 10) : 0;
}

function hasAnyFeedSeen() {
    return ['news', 'forum', 'discussion'].some(c => localStorage.getItem(feedSeenKey(c)) !== null);
}

function initFeedSeenIfNeeded() {
    if (feedSeenInitialized || !feedMetaCache?.by_category) return;
    if (hasAnyFeedSeen()) {
        feedSeenInitialized = true;
        return;
    }
    Object.keys(feedMetaCache.by_category).forEach(cat => {
        const latest = feedMetaCache.by_category[cat]?.latest_id;
        if (latest) localStorage.setItem(feedSeenKey(cat), String(latest));
    });
    feedSeenInitialized = true;
}

function markFeedCategorySeen(category) {
    const cat = category || 'forum';
    const latest = feedMetaCache?.by_category?.[cat]?.latest_id;
    if (latest) localStorage.setItem(feedSeenKey(cat), String(latest));
    updateFeedBadges();
}

function markAllFeedSeen() {
    if (!feedMetaCache?.by_category) return;
    Object.keys(feedMetaCache.by_category).forEach(cat => {
        const latest = feedMetaCache.by_category[cat]?.latest_id;
        if (latest) localStorage.setItem(feedSeenKey(cat), String(latest));
    });
    feedSeenInitialized = true;
    updateFeedBadges();
}

function setNavBadge(elId, count) {
    const el = document.getElementById(elId);
    if (!el) return;
    const n = Number(count) || 0;
    if (n > 0) {
        el.hidden = false;
        el.textContent = n > 99 ? '99+' : String(n);
    } else {
        el.hidden = true;
        el.textContent = '';
    }
}

function setTabBadge(selector, count) {
    const el = document.querySelector(selector);
    if (!el) return;
    const n = Number(count) || 0;
    el.hidden = n <= 0;
    if (n > 0) el.textContent = n > 99 ? '99+' : String(n);
}

function updateFeedBadges() {
    if (!feedMetaCache?.by_category) return;
    initFeedSeenIfNeeded();
    let homeTotal = 0;
    Object.entries(feedMetaCache.by_category).forEach(([cat, meta]) => {
        const latest = meta?.latest_id || 0;
        const seen = getFeedSeenId(cat);
        const diff = latest > seen ? 1 : 0;
        homeTotal += diff;
        setTabBadge(`.forum-tab[data-forum="${cat}"] .tab-notify`, diff);
    });
    const homeSection = document.getElementById('homeSection');
    const onHome = homeSection?.classList.contains('active');
    setNavBadge('navNotifyHome', onHome ? 0 : homeTotal);
}

function maybeNotifyNewPm(unread) {
    const n = Number(unread) || 0;
    if (n > lastPmUnread && document.hidden && typeof Notification !== 'undefined') {
        if (Notification.permission === 'granted') {
            new Notification('Мини-станция', {
                body: n === 1 ? 'Новое личное сообщение' : `Новых сообщений: ${n}`,
                icon: '/static/coin.png',
                tag: 'pm-unread',
            });
        }
    }
    lastPmUnread = n;
}

async function requestNotificationPermission() {
    if (typeof Notification === 'undefined' || Notification.permission !== 'default') return;
    try {
        await Notification.requestPermission();
    } catch {
        /* ignore */
    }
}

async function pollNotifications() {
    if (!currentUser?.authenticated) {
        setNavBadge('navNotifyMessages', 0);
        lastPmUnread = 0;
        updateFeedBadges();
        return;
    }
    try {
        await apiCall('POST', '/api/presence/heartbeat');
    } catch {
        /* ignore */
    }
    try {
        const unread = await apiCall('GET', '/api/messages/unread-count');
        const count = Number(unread.unread) || 0;
        maybeNotifyNewPm(count);
        const messagesSection = document.getElementById('messagesSection');
        const onMessages = messagesSection?.classList.contains('active');
        setNavBadge('navNotifyMessages', onMessages ? 0 : count);
    } catch {
        /* ignore */
    }
    try {
        feedMetaCache = await apiCall('GET', '/api/social/feed-updates');
        updateFeedBadges();
    } catch {
        /* ignore */
    }
}

function startNotificationPolling() {
    stopNotificationPolling();
    requestNotificationPermission();
    pollNotifications();
    notifyPollInterval = setInterval(pollNotifications, document.hidden ? 8000 : 12000);
}

function stopNotificationPolling() {
    if (notifyPollInterval) {
        clearInterval(notifyPollInterval);
        notifyPollInterval = null;
    }
}

document.addEventListener('visibilitychange', () => {
    if (!notifyPollInterval) return;
    clearInterval(notifyPollInterval);
    notifyPollInterval = setInterval(pollNotifications, document.hidden ? 8000 : 12000);
    if (!document.hidden) pollNotifications();
});

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.forum-tab[data-forum]').forEach(btn => {
        if (btn.querySelector('.tab-notify')) return;
        const dot = document.createElement('span');
        dot.className = 'tab-notify';
        dot.hidden = true;
        btn.appendChild(dot);
    });
});
