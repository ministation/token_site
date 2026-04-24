async function loadMyProfile() {
    if (!currentPlayerId) {
        alert('Привяжите Discord к игровому аккаунту');
        return;
    }
    await loadProfile(currentPlayerId);
}

async function loadProfile(playerId) {
    try {
        const resp = await fetch(`/api/social/profile/${playerId}`);
        if (!resp.ok) {
            document.getElementById('profileContent').innerHTML = '<div class="card"><h2>Профиль не найден</h2></div>';
            return;
        }
        const profile = await resp.json();
        const isOwn = currentPlayerId === profile.player_id;
        const avatarUrl = profile.discord_avatar || '/static/default_avatar.png';

        document.getElementById('profileContent').innerHTML = `
            <div class="card">
                <div class="profile-header">
                    <img src="${avatarUrl}" class="profile-avatar" onerror="this.src='/static/default_avatar.png'">
                    <div class="profile-info">
                        <h2 class="profile-name">${escapeHtml(profile.game_nickname || 'Игрок')}</h2>
                        <p style="color: #a080d0;">@${escapeHtml(profile.discord_username || 'Не привязан')}</p>
                        <div class="profile-stats">
                            <div class="profile-stat">
                                <div class="profile-stat-value">${profile.followers_count || 0}</div>
                                <div class="profile-stat-label">Подписчиков</div>
                            </div>
                            <div class="profile-stat">
                                <div class="profile-stat-value">${profile.following_count || 0}</div>
                                <div class="profile-stat-label">Подписок</div>
                            </div>
                        </div>
                        <div class="profile-actions">
                            ${isOwn ? `
                                <button class="follow-btn" onclick="editProfile()">✏️ Редактировать</button>
                            ` : `
                                <button class="follow-btn ${profile.is_following ? 'unfollow' : ''}" 
                                        onclick="toggleFollow('${profile.player_id}')">
                                    ${profile.is_following ? 'Отписаться' : 'Подписаться'}
                                </button>
                            `}
                        </div>
                    </div>
                </div>
                ${profile.bio ? `<div class="profile-bio">${escapeHtml(profile.bio)}</div>` : '<div class="profile-bio">Био пока нет...</div>'}
            </div>
            <div class="card">
                <h2>Посты</h2>
                <div id="userPosts"></div>
            </div>
        `;

        const postsResp = await fetch(`/api/social/posts/user/${playerId}`);
        const posts = await postsResp.json();
        const postsContainer = document.getElementById('userPosts');
        postsContainer.innerHTML = posts.length ? posts.map(p => renderPost(p)).join('') : '<p>Нет постов</p>';
    } catch (e) {
        console.error(e);
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