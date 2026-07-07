let currentAppealBanId = null;

async function loadBans() {
    const container = document.getElementById('bansContainer');
    if (!container) return;

    if (!currentUser?.authenticated) {
        container.innerHTML = '<p class="empty-state">Войдите через Discord, чтобы видеть свои наказания</p>';
        return;
    }

    container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const res = await fetch('/api/bans/my');
        if (res.status === 403) {
            const err = await res.json();
            container.innerHTML = `<p class="empty-state">${escapeHtml(err.detail || 'Нужна привязка к игровому аккаунту')}</p>`;
            return;
        }
        if (!res.ok) throw new Error('Ошибка загрузки');
        const bans = await res.json();
        if (!bans.length) {
            container.innerHTML = '<p class="empty-state success"><i class="fa-solid fa-check"></i> У вас нет наказаний</p>';
            return;
        }
        container.innerHTML = bans.map(b => renderBanCard(b)).join('');
    } catch (e) {
        container.innerHTML = '<p class="error">Не удалось загрузить наказания</p>';
    }
}

function renderBanCard(b, options = {}) {
    const typeClass = b.type === 0 ? 'type-server' : 'type-role';
    const typeLabel = b.type === 0 ? 'Серверный' : 'Джоббан';
    const exp = b.expiration_time ? new Date(b.expiration_time).toLocaleString('ru-RU') : 'Навсегда';
    const time = b.ban_time ? new Date(b.ban_time).toLocaleString('ru-RU') : '—';
    const roles = (b.roles && b.roles.length) ? b.roles.join(', ') : '';
    const players = (b.player_names && b.player_names.length) ? b.player_names.join(', ') : '';

    let statusHtml = '';
    if (b.is_unbanned) {
        statusHtml = '<span class="ban-status ban-status-unbanned">Снят</span>';
    } else if (b.is_active) {
        statusHtml = '<span class="ban-status ban-status-active">Активен</span>';
    } else if (b.is_active === false) {
        statusHtml = '<span class="ban-status ban-status-expired">Истёк</span>';
    }

    let appealHtml = '';
    if (b.appeal) {
        const statusLabels = { pending: 'На рассмотрении', approved: 'Одобрено', rejected: 'Отклонено' };
        appealHtml = `<div class="ban-appeal-status appeal-${b.appeal.status}">
            <b>Обжалование:</b> ${statusLabels[b.appeal.status] || b.appeal.status}
            ${b.appeal.admin_response ? '<br><b>Ответ:</b> ' + escapeHtml(b.appeal.admin_response) : ''}
        </div>`;
    } else if (currentUser?.authenticated && !options.admin && b.is_active) {
        appealHtml = `<button type="button" class="ban-appeal-btn" onclick="openAppealModal(${b.ban_id})">
            <i class="fa-solid fa-scale-balanced"></i> Обжаловать
        </button>`;
    }

    const unbanHtml = (options.admin && b.is_active)
        ? `<button type="button" class="ss14-unban-btn" onclick="unbanGameBan(${b.ban_id})">
            <i class="fa-solid fa-unlock"></i> Разбанить
           </button>`
        : '';

    return `<div class="ban-card ${typeClass}">
        <div class="ban-card-header">
            <h3 class="ban-card-title">${typeLabel} #${b.ban_id} ${statusHtml}</h3>
            <span class="ban-card-time">${time}</span>
        </div>
        ${players ? `<div class="ban-card-meta"><b>Игрок:</b> ${escapeHtml(players)}</div>` : ''}
        <div class="ban-card-meta"><b>Админ:</b> ${escapeHtml(b.admin_name || '—')}
            &nbsp;·&nbsp; <b>Срок:</b> ${exp}</div>
        ${b.is_unbanned && b.unban_time ? `<div class="ban-card-meta"><b>Снят:</b> ${new Date(b.unban_time).toLocaleString('ru-RU')}
            ${b.unban_admin_name ? ' · ' + escapeHtml(b.unban_admin_name) : ''}</div>` : ''}
        ${roles ? `<div class="ban-card-meta" style="margin-top:6px;"><b>Должности:</b> ${escapeHtml(roles)}</div>` : ''}
        <div class="ban-card-reason"><b>Причина:</b> ${escapeHtml(b.reason || '—')}</div>
        ${unbanHtml}${appealHtml}
    </div>`;
}

function openAppealModal(banId) {
    currentAppealBanId = banId;
    const modal = document.getElementById('appealModal');
    const label = document.getElementById('appealBanIdLabel');
    const text = document.getElementById('appealText');
    const result = document.getElementById('appealModalResult');
    if (label) label.textContent = banId;
    if (text) text.value = '';
    if (result) result.innerHTML = '';
    if (modal) modal.style.display = 'flex';
}

function closeAppealModal() {
    currentAppealBanId = null;
    const modal = document.getElementById('appealModal');
    if (modal) modal.style.display = 'none';
}

async function submitBanAppeal() {
    const text = document.getElementById('appealText')?.value.trim();
    const result = document.getElementById('appealModalResult');
    if (!currentAppealBanId || !text) {
        alert('Введите текст обжалования');
        return;
    }
    try {
        await apiCall('POST', '/api/bans/appeal', { ban_id: currentAppealBanId, appeal_text: text });
        closeAppealModal();
        loadBans();
    } catch (e) {
        if (result) result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}
