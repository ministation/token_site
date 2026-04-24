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
    const colors = {0: '#ce5a45', 1: '#5e98d5'};
    const names = {0: '🚨 Серверный', 1: '🎭 Ролевой'};
    const exp = b.expiration_time ? new Date(b.expiration_time).toLocaleString() : 'Навсегда';
    const time = b.ban_time ? new Date(b.ban_time).toLocaleString() : '-';
    const players = (b.players && b.players.length) ? b.players.map(id => id.substring(0,8)).join(', ') : 'Неизвестный';
    const roles = (b.roles && b.roles.length) ? b.roles.join(', ') : '';
    
    return '<div style="border-left:4px solid ' + colors[b.type] + '; margin-bottom:14px; padding:14px; background:rgba(25,18,40,0.7); border-radius:8px;">' +
        '<div style="display:flex; justify-content:space-between; margin-bottom:8px;">' +
        '<h3 style="margin:0; color:' + colors[b.type] + ';">' + names[b.type] + ' бан #' + b.ban_id + '</h3>' +
        '<span style="color:#888; font-size:0.8rem;">' + time + '</span></div>' +
        '<div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:8px;">' +
        '<div><b>Админ:</b> ' + (b.admin_name || '-') + '</div>' +
        '<div><b>Игроки:</b> ' + players + '</div>' +
        '<div><b>Срок:</b> ' + exp + '</div>' +
        (roles ? '<div><b>Роли:</b> ' + roles + '</div>' : '<div></div>') +
        '</div>' +
        '<div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px;"><b>Причина:</b> ' + (b.reason || '-') + '</div>' +
        '</div>';
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
        if (!bans.length) { c.innerHTML = '<p style="color:#4CAF50;">✅ У вас нет наказаний!</p>'; return; }
        c.innerHTML = '<h3>Ваши наказания:</h3>' + bans.map(b => renderBanCard(b)).join('');
    } catch (e) { document.getElementById('myBansContainer').innerHTML = '<p>Войдите, чтобы увидеть свои баны</p>'; }
}