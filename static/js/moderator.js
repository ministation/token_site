function initModeratorPanel() {
    if (!currentUser?.is_moderator) return;
    const navBtn = document.getElementById('moderatorNavBtn');
    if (navBtn && !currentUser?.is_admin) navBtn.style.display = '';
}

async function loadModeratorAppeals() {
    const container = document.getElementById('moderatorAppealsContent');
    if (!container) return;
    const status = document.getElementById('moderatorAppealFilter')?.value || '';
    container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const url = '/api/admin/appeals?limit=50' + (status ? '&status=' + status : '');
        const appeals = await apiCall('GET', url);
        if (!appeals.length) {
            container.innerHTML = '<p class="empty-state">Обжалований нет</p>';
            return;
        }
        container.innerHTML = appeals.map(renderAppealCard).join('');
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

function renderAppealCard(a) {
    const statusLabel = { pending: 'Ожидает', approved: 'Одобрено', rejected: 'Отклонено' }[a.status] || a.status;
    const statusClass = a.status === 'pending' ? 'appeal-pending' : (a.status === 'approved' ? 'appeal-approved' : 'appeal-rejected');
    return `
    <div class="appeal-card ${statusClass}">
        <div class="appeal-header">
            <strong>Бан #${a.ban_id}</strong> · ${escapeHtml(a.ckey || a.player_id?.slice(0, 8) || 'Игрок')}
            · <span class="appeal-status">${statusLabel}</span>
            · ${new Date(a.created_at).toLocaleString()}
        </div>
        <div class="appeal-text">${escapeHtml(a.appeal_text)}</div>
        ${a.admin_response ? `<div class="appeal-response"><b>Ответ:</b> ${escapeHtml(a.admin_response)}</div>` : ''}
        ${a.status === 'pending' ? `
        <div class="appeal-actions">
            <button type="button" class="btn-sm" onclick="reviewAppeal(${a.id}, 'approved')">Одобрить (снять бан)</button>
            <button type="button" class="btn-danger-sm" onclick="reviewAppeal(${a.id}, 'rejected')">Отклонить</button>
        </div>` : ''}
    </div>`;
}
