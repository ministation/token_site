async function searchSocial(query = '') {
    try {
        const res = await fetch('/api/social/search?q=' + encodeURIComponent(query) + '&limit=50');
        const results = await res.json();
        
        const container = document.getElementById('searchResults');
        if (!results || results.length === 0) {
            container.innerHTML = '<p style="color:#888;">Никого не найдено</p>';
            return;
        }
        
        container.innerHTML = results.map(user => {
            const nickname = user.game_nickname || user.nickname || 'Без имени';
            const username = user.discord_username || 'Не привязан';
            const avatar = user.discord_avatar || '/static/default_avatar.png';
            const balance = user.balance || 0;
            
            return '<div class="search-result-item">' +
                '<img src="' + avatar + '" class="search-avatar" onerror="this.src=\'/static/default_avatar.png\'">' +
                '<div style="flex:1;">' +
                '<div><strong>' + nickname + '</strong></div>' +
                '<div style="font-size:0.8rem; color:#888;">@' + username + '</div>' +
                '<div style="color:#fc0;">🪙 ' + balance + ' монет</div>' +
                '</div>' +
                '<button onclick="window.location.href=\'/profile/' + user.player_id + '\'" class="follow-btn">👤 Профиль</button>' +
                '</div>';
        }).join('');
    } catch (e) {
        console.error('Search error:', e);
        document.getElementById('searchResults').innerHTML = '<p style="color:#e08090;">Ошибка</p>';
    }
}

function performSocialSearch() {
    const input = document.getElementById('socialSearchInput');
    const query = input ? input.value.trim() : '';
    searchSocial(query);
}