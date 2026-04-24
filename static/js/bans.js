let bansOffset = 0;

async function loadBans() {
    try {
        const res = await fetch(`/api/bans/all?limit=20&offset=${bansOffset}`);
        const bans = await res.json();
        const container = document.getElementById('bansContainer');
        
        if (!bans.length && bansOffset === 0) {
            container.innerHTML = '<p>Банов нет.</p>';
            return;
        }
        
        const html = bans.map(b => renderBanCard(b)).join('');
        if (bansOffset === 0) container.innerHTML = html;
        else container.innerHTML += html;
        
        bansOffset += bans.length;
    } catch (e) {
        document.getElementById('bansContainer').innerHTML = '<p class="error">Ошибка загрузки</p>';
    }
}

function renderBanCard(b) {
    const typeNames = {0: 'Серверный', 1: 'Ролевой'};
    const typeColors = {0: '#ce5a45', 1: '#5e98d5'};
    const typeEmoji = {0: '🚨', 1: '🎭'};
    
    const expTime = b.expiration_time ? new Date(b.expiration_time).toLocaleString() : 'Навсегда';
    const banTime = b.ban_time ? new Date(b.ban_time).toLocaleString() : 'Неизвестно';
    
    return `
        <div class="ban-card" style="border-left: 4px solid ${typeColors[b.type]}; margin-bottom: 16px; padding: 14px; background: rgba(25,18,40,0.7); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin:0; color: ${typeColors[b.type]};">${typeEmoji[b.type]} ${typeNames[b.type]} бан #${b.ban_id}</h3>
                <span style="color:#888; font-size:0.8rem;">${banTime}</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
                <div><strong>Админ:</strong> ${b.admin_name}</div>
                <div><strong>Игрок:</strong> ${b.player_name}</div>
                <div><strong>Срок:</strong> ${expTime}</div>
                ${b.roles?.length ? `<div><strong>Роли:</strong> ${b.roles.join(', ')}</div>` : ''}
            </div>
            <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px;">
                <strong>Причина:</strong> ${b.reason || 'Не указана'}
            </div>
        </div>
    `;
}

function loadMoreBans() {
    loadBans();
}

async function loadMyBans() {
    try {
        const res = await fetch('/api/bans/my');
        const bans = await res.json();
        const container = document.getElementById('myBansContainer');
        if (!bans.length) {
            container.innerHTML = '<p>У вас нет наказаний! 🎉</p>';
            return;
        }
        container.innerHTML = bans.map(b => renderBanCard(b)).join('');
    } catch (e) {
        document.getElementById('myBansContainer').innerHTML = '<p class="error">Ошибка загрузки</p>';
    }
}