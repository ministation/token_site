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
    } catch (e) {
        document.getElementById('bansContainer').innerHTML = '<p class="error">Ошибка</p>';
    }
}

function renderBanCard(b) {
    var colors = {0: '#ce5a45', 1: '#5e98d5'};
    var names = {0: 'Серверный', 1: 'Ролевой'};
    var exp = b.expiration_time ? new Date(b.expiration_time).toLocaleString() : 'Навсегда';
    var time = b.ban_time ? new Date(b.ban_time).toLocaleString() : '-';
    return '<div style="border-left:4px solid ' + colors[b.type] + '; margin-bottom:16px; padding:14px; background:rgba(25,18,40,0.7); border-radius:8px;">' +
        '<div style="display:flex; justify-content:space-between;"><h3 style="color:' + colors[b.type] + ';">' + names[b.type] + ' бан #' + b.ban_id + '</h3><span style="color:#888;">' + time + '</span></div>' +
        '<div><b>Админ:</b> ' + (b.admin_name || '-') + ' | <b>Игрок:</b> ' + (b.player_name || '-') + ' | <b>Срок:</b> ' + exp + '</div>' +
        '<div style="background:rgba(0,0,0,0.3); padding:10px; margin-top:8px;"><b>Причина:</b> ' + (b.reason || '-') + '</div></div>';
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
        var res = await fetch('/api/bans/my');
        var bans = await res.json();
        var c = document.getElementById('myBansContainer');
        if (!bans.length) { c.innerHTML = '<p style="color:#4CAF50;">✅ У вас нет наказаний!</p>'; return; }
        c.innerHTML = '<h3>Ваши наказания:</h3>' + bans.map(b => renderBanCard(b)).join('');
    } catch (e) {
        document.getElementById('myBansContainer').innerHTML = '<p>Войдите, чтобы увидеть свои баны</p>';
    }
}