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
        const myId = currentUser?.social_id || currentPlayerId;
        const isOwn = !!(p.is_own || (myId && myId === p.player_id));
        const showInventory = isOwn;

        const panels = document.getElementById('inventoryPanels');
        const avatarSection = document.getElementById('avatarSection');
        if (avatarSection) avatarSection.style.display = showInventory ? '' : 'none';
        if (showInventory && typeof loadInventory === 'function') loadInventory();

        const badgesHtml = typeof renderBadgesHtml === 'function'
            ? renderBadgesHtml(p.badges, 'profile-page-badge')
            : '';
        const joined = p.created_at
            ? new Date(p.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
            : '—';

        const banActions = currentUser?.is_admin && !isOwn && p.discord_id ? `
                            ${p.site_banned
                                ? `<button type="button" class="btn-sm" onclick='adminUnbanFromProfile(${JSON.stringify(p.discord_id)})'>
                                    <i class="fa-solid fa-unlock"></i> Разбанить на сайте
                                   </button>`
                                : `<button type="button" class="btn-sm profile-ban-btn" onclick='adminBanFromProfile(${JSON.stringify(p.player_id)}, ${JSON.stringify(p.discord_id)}, ${JSON.stringify(p.game_nickname || p.discord_username || "Игрок")})'>
                                    <i class="fa-solid fa-ban"></i> Бан на сайте
                                   </button>`}
                        ` : '';

        container.innerHTML = `
            <div class="profile-page-hero">
                ${typeof chatAvatarHtml === 'function'
                    ? chatAvatarHtml(avatarUrl, 'profile-avatar profile-page-avatar', p.presence || 'offline')
                    : `<img src="${escapeHtml(avatarUrl)}" class="profile-avatar profile-page-avatar" alt="" onerror="this.src='/static/default_avatar.png'">`}
                <div class="profile-info profile-page-info">
                    <div class="profile-page-name-row">
                        <h2>${escapeHtml(p.game_nickname || 'Игрок')}</h2>
                        ${badgesHtml ? `<div class="profile-page-badges">${badgesHtml}</div>` : ''}
                    </div>
                    <p class="profile-username">@${escapeHtml(p.discord_username || 'не привязан')}</p>
                    <p class="profile-joined"><i class="fa-solid fa-calendar"></i> На сайте с ${joined}</p>
                    <div class="profile-stats">
                        <button type="button" class="profile-stat profile-stat-btn" onclick='loadProfileFollowers(${JSON.stringify(p.player_id)})'>
                            <div class="profile-stat-value">${p.followers_count || 0}</div>
                            <div class="profile-stat-label">Подписчиков</div>
                        </button>
                        <button type="button" class="profile-stat profile-stat-btn" onclick='loadProfileFollowing(${JSON.stringify(p.player_id)})'>
                            <div class="profile-stat-value">${p.following_count || 0}</div>
                            <div class="profile-stat-label">Подписок</div>
                        </button>
                    </div>
                    <div class="profile-actions">
                        ${!isOwn ? `
                            <button type="button" class="follow-btn ${p.is_following ? 'unfollow' : ''}"
                                onclick='toggleProfileFollow(${JSON.stringify(p.player_id)})'>
                                ${p.is_following ? 'Отписаться' : 'Подписаться'}
                            </button>
                            <button type="button" class="message-btn"
                                onclick='startConversationWith(${JSON.stringify(p.player_id)}, ${JSON.stringify(p.game_nickname || 'Игрок')})'>
                                <i class="fa-solid fa-envelope"></i> Написать
                            </button>
                            ${banActions}
                        ` : `
                            <button type="button" class="btn-sm" onclick='editProfileBio(${JSON.stringify(p.player_id)})'>
                                <i class="fa-solid fa-pen"></i> Изменить био
                            </button>
                        `}
                    </div>
                </div>
            </div>
            ${p.site_banned && currentUser?.is_admin ? `
                <div class="profile-banned-banner">
                    <i class="fa-solid fa-ban" aria-hidden="true"></i>
                    <div><strong>Забанен на сайте.</strong> ${escapeHtml(p.site_ban_reason || 'Причина не указана')}</div>
                </div>
            ` : ''}
            <div class="profile-bio-block" id="profileBioBlock">
                ${p.bio
                    ? `<div class="profile-bio">${formatMessageContent(p.bio)}</div>`
                    : `<p class="empty-state profile-bio-empty">${isOwn ? 'Расскажите о себе — нажмите «Изменить био»' : 'Биография пуста'}</p>`}
            </div>
        `;

        const sectionRoot = document.getElementById('inventorySection') || container.parentElement;
        let postsCard = document.getElementById('profilePostsCard');
        if (!postsCard && sectionRoot) {
            postsCard = document.createElement('div');
            postsCard.id = 'profilePostsCard';
            postsCard.className = 'card profile-posts-card';
            sectionRoot.appendChild(postsCard);
        }
        if (postsCard) {
            postsCard.innerHTML = `
                <section class="profile-posts-section">
                    <h3><i class="fa-solid fa-newspaper"></i> Записи</h3>
                    <div id="profilePostsList"><p class="empty-state">Загрузка...</p></div>
                </section>
            `;
            postsCard.hidden = false;
        }

        if (panels && sectionRoot) {
            // Order: profile → inventory → posts
            sectionRoot.appendChild(container);
            if (showInventory) {
                panels.hidden = false;
                sectionRoot.appendChild(panels);
            } else {
                panels.hidden = true;
                sectionRoot.appendChild(panels);
            }
            if (postsCard) sectionRoot.appendChild(postsCard);
        }

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
            <button type="button" class="btn-sm" onclick='loadProfilePosts(${JSON.stringify(currentProfileId)})'>К записям</button>
        </div>
        ${users.map(u => `
            <button type="button" class="profile-user-list-item" onclick='openProfile(${JSON.stringify(u.player_id)})'>
                ${typeof chatAvatarHtml === 'function'
                    ? chatAvatarHtml(u.discord_avatar, 'profile-list-avatar', u.presence || 'offline')
                    : `<img src="${escapeHtml(u.discord_avatar || '/static/default_avatar.png')}" alt="" onerror="this.onerror=null;this.src='/static/default_avatar.png'">`}
                <span>${escapeHtml(u.game_nickname || u.discord_username || 'Игрок')}</span>
            </button>
        `).join('')}
    `;
}

async function adminBanFromProfile(playerId, discordId, displayName) {
    if (!currentUser?.is_admin) return;
    const reason = prompt(`Причина бана на сайте для ${displayName || 'игрока'}:`, 'Нарушение правил');
    if (reason === null) return;
    const trimmed = reason.trim();
    if (trimmed.length < 3) {
        alert('Укажите причину (минимум 3 символа)');
        return;
    }
    if (!confirm(`Забанить ${displayName || 'игрока'} на сайте? Сессии будут сброшены.`)) return;
    try {
        await apiCall('POST', '/api/admin/site-bans', {
            player_id: playerId,
            discord_id: discordId,
            reason: trimmed,
        });
        await loadProfile(playerId);
    } catch (e) {
        alert(e.message);
    }
}

async function adminUnbanFromProfile(discordId) {
    if (!currentUser?.is_admin) return;
    if (!confirm('Снять бан с сайта?')) return;
    try {
        await apiCall('POST', '/api/admin/site-bans/unban', { discord_id: discordId });
        if (currentProfileId) await loadProfile(currentProfileId);
    } catch (e) {
        alert(e.message);
    }
}
