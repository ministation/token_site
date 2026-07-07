let currentProfileId = null;

async function loadMyProfile() {
    const id = currentUser?.social_id || currentPlayerId;
    if (!id) {
        document.getElementById('profileContent').innerHTML =
            '<p class="empty-state">Войдите через Discord, чтобы видеть профиль</p>';
        return;
    }
    await loadProfile(id);
}

async function loadProfile(playerId) {
    const container = document.getElementById('profileContent');
    if (!container) return;
    if (!playerId) {
        container.innerHTML = '<p class="empty-state">Профиль недоступен</p>';
        return;
    }
    currentProfileId = playerId;
    container.innerHTML = '<p class="empty-state">Загрузка...</p>';

    try {
        const p = await apiCall('GET', `/api/social/profile/${encodeURIComponent(playerId)}`);
        const avatarUrl = p.discord_avatar || '/static/default_avatar.png';
        const isOwn = !!p.is_own;
        const myId = currentUser?.social_id || currentPlayerId;
        const showInventory = isOwn || myId === p.player_id;

        const panels = document.getElementById('inventoryPanels');
        const avatarSection = document.getElementById('avatarSection');
        if (panels) panels.hidden = !showInventory;
        if (avatarSection) avatarSection.style.display = showInventory ? '' : 'none';
        if (showInventory && typeof loadInventory === 'function') loadInventory();

        const badgesHtml = typeof renderBadgesHtml === 'function'
            ? renderBadgesHtml(p.badges, 'profile-page-badge')
            : '';
        const joined = p.created_at
            ? new Date(p.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
            : '—';

        container.innerHTML = `
            <div class="profile-page-hero">
                <img src="${avatarUrl}" class="profile-avatar profile-page-avatar" alt=""
                     onerror="this.src='/static/default_avatar.png'">
                <div class="profile-info profile-page-info">
                    <div class="profile-page-name-row">
                        <h2>${escapeHtml(p.game_nickname || 'Игрок')}</h2>
                        ${badgesHtml ? `<div class="profile-page-badges">${badgesHtml}</div>` : ''}
                    </div>
                    <p class="profile-username">@${escapeHtml(p.discord_username || 'не привязан')}</p>
                    <p class="profile-joined"><i class="fa-solid fa-calendar"></i> На сайте с ${joined}</p>
                    <div class="profile-stats">
                        <button type="button" class="profile-stat profile-stat-btn" onclick="loadProfileFollowers('${p.player_id}')">
                            <div class="profile-stat-value">${p.followers_count || 0}</div>
                            <div class="profile-stat-label">Подписчиков</div>
                        </button>
                        <button type="button" class="profile-stat profile-stat-btn" onclick="loadProfileFollowing('${p.player_id}')">
                            <div class="profile-stat-value">${p.following_count || 0}</div>
                            <div class="profile-stat-label">Подписок</div>
                        </button>
                    </div>
                    <div class="profile-actions">
                        ${!isOwn ? `
                            <button type="button" class="follow-btn ${p.is_following ? 'unfollow' : ''}"
                                onclick="toggleProfileFollow('${p.player_id}')">
                                ${p.is_following ? 'Отписаться' : 'Подписаться'}
                            </button>
                            <button type="button" class="message-btn"
                                onclick='startConversationWith(${JSON.stringify(p.player_id)}, ${JSON.stringify(p.game_nickname || 'Игрок')})'>
                                <i class="fa-solid fa-envelope"></i> Написать
                            </button>
                        ` : `
                            <button type="button" class="btn-sm" onclick="editProfileBio('${p.player_id}')">
                                <i class="fa-solid fa-pen"></i> Изменить био
                            </button>
                        `}
                    </div>
                </div>
            </div>
            <div class="profile-bio-block" id="profileBioBlock">
                ${p.bio
                    ? `<div class="profile-bio">${formatMessageContent(p.bio)}</div>`
                    : `<p class="empty-state profile-bio-empty">${isOwn ? 'Расскажите о себе — нажмите «Изменить био»' : 'Биография пуста'}</p>`}
            </div>
            <section class="profile-posts-section">
                <h3><i class="fa-solid fa-newspaper"></i> Записи</h3>
                <div id="profilePostsList"><p class="empty-state">Загрузка...</p></div>
            </section>
        `;
        loadProfilePosts(playerId);
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message || 'Профиль не найден')}</p>`;
    }
}

async function loadProfilePosts(playerId) {
    const list = document.getElementById('profilePostsList');
    if (!list) return;
    try {
        const posts = await apiCall('GET', `/api/social/posts/user/${encodeURIComponent(playerId)}`);
        if (!posts.length) {
            list.innerHTML = '<p class="empty-state">Записей пока нет</p>';
            return;
        }
        if (typeof renderPosts === 'function') {
            renderPosts(posts, 'profilePostsList');
        } else {
            list.innerHTML = posts.map(p => `<div class="card forum-post">${escapeHtml(p.content)}</div>`).join('');
        }
    } catch {
        list.innerHTML = '<p class="error">Не удалось загрузить записи</p>';
    }
}

async function toggleProfileFollow(targetId) {
    try {
        const p = await apiCall('GET', `/api/social/profile/${encodeURIComponent(targetId)}`);
        if (p.is_following) {
            await apiCall('DELETE', `/api/social/follow/${encodeURIComponent(targetId)}`);
        } else {
            await apiCall('POST', `/api/social/follow/${encodeURIComponent(targetId)}`);
        }
        loadProfile(targetId);
    } catch (e) {
        alert(e.message);
    }
}

async function editProfileBio(playerId) {
    const current = document.querySelector('#profileBioBlock .profile-bio')?.innerText || '';
    const bio = prompt('Ваша биография:', current);
    if (bio === null) return;
    try {
        await apiCall('POST', '/api/social/profile/update', { bio: bio.trim() });
        loadProfile(playerId);
    } catch (e) {
        alert(e.message);
    }
}

async function loadProfileFollowers(playerId) {
    try {
        const users = await apiCall('GET', `/api/social/followers/${encodeURIComponent(playerId)}`);
        showProfileUserList('Подписчики', users);
    } catch (e) {
        alert(e.message);
    }
}

async function loadProfileFollowing(playerId) {
    try {
        const users = await apiCall('GET', `/api/social/following/${encodeURIComponent(playerId)}`);
        showProfileUserList('Подписки', users);
    } catch (e) {
        alert(e.message);
    }
}

function showProfileUserList(title, users) {
    const list = document.getElementById('profilePostsList');
    if (!list) return;
    if (!users.length) {
        list.innerHTML = `<p class="empty-state">${escapeHtml(title)}: пусто</p>`;
        return;
    }
    list.innerHTML = `
        <div class="profile-user-list-head">
            <strong>${escapeHtml(title)}</strong>
            <button type="button" class="btn-sm" onclick="loadProfilePosts('${currentProfileId}')">К записям</button>
        </div>
        ${users.map(u => `
            <button type="button" class="profile-user-list-item" onclick="openProfile(${JSON.stringify(u.player_id)})">
                <img src="${u.discord_avatar || '/static/default_avatar.png'}" alt="" onerror="this.src='/static/default_avatar.png'">
                <span>${escapeHtml(u.game_nickname || u.discord_username || 'Игрок')}</span>
            </button>
        `).join('')}
    `;
}
