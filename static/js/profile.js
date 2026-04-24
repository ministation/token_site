async function loadMyProfile() {
    if (!currentPlayerId) {
        console.log('currentPlayerId is empty, cannot load profile');
        return;
    }
    await loadProfile(currentPlayerId);
}

async function loadProfile(playerId) {
    if (!playerId) {
        document.getElementById('profileContent').innerHTML = '<div class="card"><h2>Профиль недоступен</h2></div>';
        return;
    }
    
    try {
        const resp = await fetch(`/api/social/profile/${playerId}`);
        if (!resp.ok) {
            document.getElementById('profileContent').innerHTML = '<div class="card"><h2>Профиль не найден</h2></div>';
            return;
        }
        const p = await resp.json();
        const avatarUrl = p.discord_avatar || '/static/default_avatar.png';
        const isOwn = currentPlayerId === p.player_id;

        document.getElementById('profileContent').innerHTML = `
            <div class="card">
                <div class="profile-header">
                    <img src="${avatarUrl}" class="profile-avatar" onerror="this.src='/static/default_avatar.png'">
                    <div class="profile-info">
                        <h2>${escapeHtml(p.game_nickname || 'Игрок')}</h2>
                        <p style="color:#a080d0;">@${escapeHtml(p.discord_username || 'Не привязан')}</p>
                        <div class="profile-stats">
                            <div class="profile-stat">
                                <div class="profile-stat-value">${p.followers_count || 0}</div>
                                <div class="profile-stat-label">Подписчиков</div>
                            </div>
                            <div class="profile-stat">
                                <div class="profile-stat-value">${p.following_count || 0}</div>
                                <div class="profile-stat-label">Подписок</div>
                            </div>
                        </div>
                        <div class="profile-actions">
                            ${!isOwn ? `
                                <button class="follow-btn ${p.is_following ? 'unfollow' : ''}" onclick="toggleFollow('${p.player_id}')">
                                    ${p.is_following ? 'Отписаться' : 'Подписаться'}
                                </button>
                                <button class="message-btn" onclick="openMessageModal('${p.player_id}', '${escapeHtml(p.game_nickname)}')">
                                    💬 Написать
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
                ${p.bio ? `<div class="profile-bio">${escapeHtml(p.bio)}</div>` : ''}
            </div>
        `;
    } catch(e) {
        document.getElementById('profileContent').innerHTML = '<div class="card"><h2>Ошибка загрузки</h2></div>';
    }
}

async function toggleFollow(targetId) {
    const btn = event.target;
    const isFollowing = btn.textContent.includes('Отписаться');
    try {
        if (isFollowing) {
            await apiCall('DELETE', `/api/social/follow/${targetId}`);
        } else {
            await apiCall('POST', `/api/social/follow/${targetId}`);
        }
        loadProfile(targetId);
    } catch (e) { alert(e.message); }
}

function openMessageModal(playerId, nickname) {
    const message = prompt(`Сообщение для ${nickname}:`);
    if (!message || !message.trim()) return;
    sendMessage(playerId, message.trim());
}

async function sendMessage(playerId, content) {
    try {
        await apiCall('POST', '/api/messages/send', { receiver_id: playerId, content });
        alert('✅ Сообщение отправлено!');
    } catch (e) {
        alert('❌ ' + e.message);
    }
}