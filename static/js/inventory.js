async function loadInventory() {
    const container = document.getElementById('inventoryContent');
    if (!container) return;
    const avatarSection = document.getElementById('avatarSection');
    const avatarPreview = document.getElementById('profileAvatarPreview');
    if (!currentUser?.authenticated) {
        container.innerHTML = '<p class="empty-state">Войдите через Discord</p>';
        if (avatarSection) avatarSection.style.display = 'none';
        return;
    }
    if (avatarSection) avatarSection.style.display = 'block';
    if (avatarPreview && currentUser.avatar) avatarPreview.src = currentUser.avatar;
    container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const data = await apiCall('GET', '/api/inventory');
        let html = '';

        html += '<div class="inventory-section">';
        html += '<h3><i class="fa-solid fa-heart"></i> Донат-подписка</h3>';
        if (data.sponsor) {
            html += `
                <div class="sponsor-current">
                    <img src="${data.sponsor.icon}" alt="${escapeHtml(data.sponsor.name)}" class="sponsor-icon-large">
                    <div>
                        <div class="sponsor-level-badge">Уровень ${data.sponsor.level}</div>
                        <div class="sponsor-name">${escapeHtml(data.sponsor.name)}</div>
                    </div>
                </div>`;
        } else {
            html += '<p class="inventory-empty">Подписка не активна</p>';
        }
        html += '<div class="sponsor-tiers">';
        (data.tiers || []).forEach(t => {
            html += `
                <div class="sponsor-tier ${t.active ? 'active' : ''}">
                    <img src="${t.icon}" alt="${escapeHtml(t.name)}" class="sponsor-tier-icon">
                    <span class="sponsor-tier-level">${t.level}</span>
                    <span class="sponsor-tier-name">${escapeHtml(t.name)}</span>
                </div>`;
        });
        html += '</div></div>';

        html += '<div class="inventory-section">';
        html += '<h3><i class="fa-solid fa-ticket"></i> Билеты на антагов</h3>';
        if (!data.has_game_link) {
            html += '<p class="inventory-empty">Привяжите Discord к игровому аккаунту, чтобы видеть билеты.</p>';
        } else if (data.tickets?.length) {
            html += '<div class="tickets-grid">';
            data.tickets.forEach(t => {
                html += `
                    <div class="ticket-card" style="--ticket-color: ${t.color || '#5b8def'}">
                        <div class="ticket-icon"><i class="fa-solid ${t.icon || 'fa-ticket'}"></i></div>
                        <div class="ticket-name">${escapeHtml(t.name)}</div>
                        <div class="ticket-amount">×${t.amount}</div>
                    </div>`;
            });
            html += '</div>';
        } else {
            html += '<p class="inventory-empty">Нет активных билетов на антагов</p>';
        }
        html += '</div>';

        html += '<div class="inventory-section">';
        html += '<h3><i class="fa-solid fa-ghost"></i> Custom Ghost</h3>';
        if (!data.has_game_link) {
            html += '<p class="inventory-empty">Привяжите Discord к игровому аккаунту.</p>';
        } else if (data.custom_ghosts?.length) {
            html += '<div class="ghosts-grid">';
            data.custom_ghosts.forEach(g => {
                const amount = g.amount > 1 ? `<span class="ghost-amount">×${g.amount}</span>` : '';
                const iconHtml = g.icon
                    ? `<img src="${g.icon}" alt="" class="ghost-img" onerror="this.replaceWith(Object.assign(document.createElement('i'),{className:'fa-solid fa-ghost ghost-icon-fallback'}))">`
                    : '<i class="fa-solid fa-ghost ghost-icon-fallback"></i>';
                html += `
                    <div class="ghost-card">
                        ${iconHtml}
                        <div class="ghost-name">${escapeHtml(g.name)}</div>
                        ${amount}
                    </div>`;
            });
            html += '</div>';
        } else {
            html += '<p class="inventory-empty">Нет разблокированных custom ghost</p>';
        }
        html += '</div>';

        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function uploadAvatar() {
    const input = document.getElementById('avatarUpload');
    const result = document.getElementById('avatarUploadResult');
    if (!input?.files?.[0]) { alert('Выберите изображение'); return; }
    const formData = new FormData();
    formData.append('image', input.files[0]);
    try {
        const data = await apiCall('POST', '/api/social/profile/avatar', formData);
        if (currentUser) currentUser.avatar = data.avatar;
        const preview = document.getElementById('profileAvatarPreview');
        if (preview) preview.src = data.avatar + '?t=' + Date.now();
        const panelImg = document.querySelector('#userPanel img');
        if (panelImg) panelImg.src = data.avatar + '?t=' + Date.now();
        if (result) result.innerHTML = '<p class="success">Аватар обновлён</p>';
        input.value = '';
    } catch (e) {
        if (result) result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}
