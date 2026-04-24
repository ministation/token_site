async function searchSocial(query = '') {
    try {
        let url;
        if (query && query.length >= 1) {
            url = `/api/social/search?q=${encodeURIComponent(query)}&limit=50`;
        } else {
            url = '/api/social/search?q=&limit=50';  // пустой запрос — все игроки
        }
        
        const res = await fetch(url);
        if (!res.ok) throw new Error('Search failed');
        const results = await res.json();
        
        const container = document.getElementById('searchResults');
        if (!results || results.length === 0) {
            container.innerHTML = '<p style="color:#888;">Никого не найдено</p>';
            return;
        }
        
        container.innerHTML = results.map(user => `
            <div class="search-result-item">
                <img src="${user.discord_avatar || '/static/default_avatar.png'}" 
                     class="search-avatar" alt="" 
                     onerror="this.src='/static/default_avatar.png'">
                <div style="flex:1;">
                    <div><strong>${user.game_nickname || user.nickname || 'Без имени'}</strong></div>
                    <div style="font-size:0.8rem; color:#888;">@${user.discord_username || 'Не привязан'}</div>
                    ${user.balance !== undefined ? `<div style="color:#fc0;">🪙 ${user.balance} монет</div>` : ''}
                </div>
                <button onclick="window.location.href='/profile/${user.player_id}'" class="follow-btn">👤 Профиль</button>
            </div>
        `).join('');
    } catch (e) {
        console.error('Search error:', e);
        document.getElementById('searchResults').innerHTML = '<p style="color:#e08090;">Ошибка при поиске</p>';
    }
}

function performSocialSearch() {
    const query = document.getElementById('socialSearchInput')?.value?.trim() || '';
    searchSocial(query);
}