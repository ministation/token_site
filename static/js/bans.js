let bansOffset = 0;

async function loadBans() {
    try {
        bansOffset = 0;
        const res = await fetch('/api/bans/all?limit=20&offset=0');
        const bans = await res.json();
        const container = document.getElementById('bansContainer');
        if (!bans.length) { container.innerHTML = '<p>Банов нет.</p>'; return; }
        container.innerHTML = bans.map(b => renderBanCard(b)).join('');
        bansOffset = bans.length;
        loadMyBans();
    } catch (e) { document.getElementById('bansContainer').innerHTML = '<p class="error">Ошибка</p>'; }
}

function renderBanCard(b) {
    const typeClass = b.type === 0 ? 'type-server' : 'type-role';
    const names = {0: '🚨 Серверный', 1: '🎭 Ролевой'};
    const exp = b.expiration_time ? new Date(b.expiration_time).toLocaleString() : 'Навсегда';
    const time = b.ban_time ? new Date(b.ban_time).toLocaleString() : '-';
    const players = (b.player_names && b.player_names.length) ? b.player_names.join(', ') : 'Неизвестный';
    const roles = (b.roles && b.roles.length) ? b.roles.join(', ') : '';

    return '<div class="ban-card ' + typeClass + '">' +
        '<div class="ban-card-header">' +
        '<h3 class="ban-card-title">' + names[b.type] + ' бан #' + b.ban_id + '</h3>' +
        '<span class="ban-card-time">' + time + '</span></div>' +
        '<div class="ban-card-meta"><b>Админ:</b> ' + (b.admin_name || '-') +
        ' &nbsp;·&nbsp; <b>Игроки:</b> ' + players +
        ' &nbsp;·&nbsp; <b>Срок:</b> ' + exp + '</div>' +
        (roles ? '<div class="ban-card-meta" style="margin-top:6px;"><b>Роли:</b> ' + roles + '</div>' : '') +
        '<div class="ban-card-reason"><b>Причина:</b> ' + (b.reason || '-') + '</div></div>';
}

function loadMoreBans() {
    fetch('/api/bans/all?limit=20&offset=' + bansOffset)
        .then(r => r.json())
        .then(bans => {
            if (!bans.length) return;
            document.getElementById('bansContainer').innerHTML += bans.map(b => renderBanCard(b)).join('');
            bansOffset += bans.length;
        });
}

async function loadMyBans() {
    try {
        const res = await fetch('/api/bans/my');
        const bans = await res.json();
        const c = document.getElementById('myBansContainer');
        if (!bans.length) { c.innerHTML = '<p class="empty-state success">✅ У вас нет наказаний!</p>'; return; }
        c.innerHTML = bans.map(b => renderBanCard(b)).join('');
    } catch (e) { document.getElementById('myBansContainer').innerHTML = '<p>Войдите, чтобы увидеть свои баны</p>'; }
}