async function searchSocial() {
    const query = document.getElementById('socialSearchInput').value.trim();
    if (query.length < 2) {
        alert('Введите минимум 2 символа');
        return;
    }
    try {
        const results = await apiCall('GET', `/api/social/search?q=${encodeURIComponent(query)}`);
        const container = document.getElementById('searchResults');
        if (!results.length) {
            container.innerHTML = '<p>Ничего не найдено</p>';
            return;
        }
        container.innerHTML = results.map(user => `
            <div class="search-result-item">
                <img src="${user.discord_avatar || '/static/default_avatar.png'}" class="search-avatar" alt="" onerror="this.src='/static/default_avatar.png'">
                <div style="flex:1;">
                    <div><strong>${user.game_nickname || user.nickname || 'Без имени'}</strong></div>
                    <div style="font-size:0.8rem; color:#888;">@${user.discord_username || 'Не привязан'}</div>
                    ${user.balance !== undefined ? `<div style="color:#fc0;">🪙 ${user.balance} монет</div>` : ''}
                </div>
                <button onclick="window.location.href='/profile/${user.player_id}'" class="follow-btn">👤 Профиль</button>
            </div>
        `).join('');
    } catch (e) {
        console.error(e);
        document.getElementById('searchResults').innerHTML = '<p style="color:#e08090;">Ошибка при поиске</p>';
    }
}