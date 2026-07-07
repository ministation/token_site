let playtimeOverview = null;
let playtimeRoleFilter = '';

function canManagePlaytime() {
    return !!(currentUser?.is_time_keeper || currentUser?.is_admin);
}

function playtimeRoleRow(role) {
    const checked = role._selected ? ' checked' : '';
    const minutes = role._transferMinutes ?? '';
    const unlocked = role.unlocked
        ? '<span class="playtime-unlocked-badge">открыта</span>'
        : `<span class="playtime-deficit" title="${escapeHtml(role.unlock_hint || '')}">−${role.deficit_minutes} м</span>`;
    return `
        <tr class="playtime-role-row${role._hidden ? ' hidden' : ''}" data-tracker="${escapeHtml(role.tracker)}">
            <td class="playtime-col-check">
                <input type="checkbox" class="playtime-role-check"${checked}
                    onchange="togglePlaytimeRole('${escapeHtml(role.tracker)}', this.checked)">
            </td>
            <td class="playtime-col-icon">
                <img src="${escapeHtml(role.icon)}" alt="" class="playtime-job-icon"
                     onerror="this.src='/static/job_icons/Unknown.png'">
            </td>
            <td class="playtime-col-name">${escapeHtml(role.label)}</td>
            <td class="playtime-col-current">${escapeHtml(role.time_text)}</td>
            <td class="playtime-col-status">${unlocked}</td>
            <td class="playtime-col-transfer">
                <input type="number" class="playtime-role-minutes" min="0" step="1"
                    value="${minutes}" placeholder="0"
                    oninput="setPlaytimeRoleMinutes('${escapeHtml(role.tracker)}', this.value)">
            </td>
        </tr>
    `;
}

function renderPlaytimeRolesTable() {
    const container = document.getElementById('playtimeRolesTable');
    if (!container || !playtimeOverview?.roles?.length) {
        if (container) container.innerHTML = '';
        return;
    }

    const q = playtimeRoleFilter.trim().toLowerCase();
    for (const role of playtimeOverview.roles) {
        role._hidden = !!(q && !role.label.toLowerCase().includes(q) && !role.role_id.toLowerCase().includes(q));
    }

    const visible = playtimeOverview.roles.filter(r => !r._hidden);
    const totalSelected = visible.filter(r => r._selected).length;
    const selectAll = document.getElementById('playtimeSelectAll');
    if (selectAll) {
        selectAll.indeterminate = totalSelected > 0 && totalSelected < visible.length;
        selectAll.checked = visible.length > 0 && totalSelected === visible.length;
    }

    container.innerHTML = `
        <table class="playtime-roles-table">
            <thead>
                <tr>
                    <th></th>
                    <th></th>
                    <th>Роль</th>
                    <th>Сейчас</th>
                    <th>Статус</th>
                    <th>Перенести (мин)</th>
                </tr>
            </thead>
            <tbody>
                ${playtimeOverview.roles.map(playtimeRoleRow).join('')}
            </tbody>
        </table>
        <p class="playtime-unlock-hint">Требования к ролям взяты из билда <a href="https://github.com/ministation/mini-station-goob" target="_blank" rel="noopener">mini-station-goob</a>. Наведите на «−N м», чтобы увидеть условие.</p>
    `;
}

function renderPlaytimeSources() {
    const select = document.getElementById('playtimeFromTracker');
    const row = document.getElementById('playtimeSourceRow');
    if (!select || !row) return;

    const sources = playtimeOverview?.sources || [];
    if (!sources.length) {
        row.hidden = true;
        select.innerHTML = '';
        return;
    }

    row.hidden = false;
    const current = select.value;
    select.innerHTML = sources.map(s => `
        <option value="${escapeHtml(s.tracker)}">
            ${escapeHtml(s.label)} — ${escapeHtml(s.time_text)}
        </option>
    `).join('');
    if (current && sources.some(s => s.tracker === current)) {
        select.value = current;
    }
}

function getPlaytimeRole(tracker) {
    return playtimeOverview?.roles?.find(r => r.tracker === tracker);
}

function togglePlaytimeRole(tracker, selected) {
    const role = getPlaytimeRole(tracker);
    if (role) role._selected = selected;
    renderPlaytimeRolesTable();
}

function setPlaytimeRoleMinutes(tracker, value) {
    const role = getPlaytimeRole(tracker);
    if (!role) return;
    const minutes = parseFloat(value);
    role._transferMinutes = Number.isFinite(minutes) && minutes > 0 ? minutes : '';
    if (role._transferMinutes) role._selected = true;
    const selectAll = document.getElementById('playtimeSelectAll');
    if (selectAll) renderPlaytimeRolesTable();
}

function togglePlaytimeSelectAll() {
    const checked = document.getElementById('playtimeSelectAll')?.checked;
    if (!playtimeOverview?.roles) return;
    const fromTracker = document.getElementById('playtimeFromTracker')?.value;
    for (const role of playtimeOverview.roles) {
        if (role._hidden || role.tracker === fromTracker) continue;
        role._selected = !!checked;
    }
    renderPlaytimeRolesTable();
}

function filterPlaytimeRoles() {
    playtimeRoleFilter = document.getElementById('playtimeRoleSearch')?.value || '';
    renderPlaytimeRolesTable();
}

function applyPlaytimeBulkMinutes() {
    const minutes = parseFloat(document.getElementById('playtimeBulkMinutes')?.value || '0');
    if (!minutes || minutes <= 0) {
        alert('Укажите количество минут');
        return;
    }
    const fromTracker = document.getElementById('playtimeFromTracker')?.value;
    if (!playtimeOverview?.roles) return;
    for (const role of playtimeOverview.roles) {
        if (!role._selected || role.tracker === fromTracker) continue;
        role._transferMinutes = minutes;
    }
    renderPlaytimeRolesTable();
}

function collectPlaytimeTransfers() {
    const fromTracker = document.getElementById('playtimeFromTracker')?.value;
    if (!fromTracker) {
        throw new Error('Выберите роль, откуда переносить время');
    }
    const transfers = [];
    for (const role of playtimeOverview?.roles || []) {
        if (role.tracker === fromTracker) continue;
        if (!role._selected) continue;
        const minutes = parseFloat(role._transferMinutes);
        if (!minutes || minutes <= 0) continue;
        transfers.push({ to_tracker: role.tracker, minutes });
    }
    if (!transfers.length) {
        throw new Error('Отметьте роли и укажите минуты для переноса');
    }
    return { fromTracker, transfers };
}

async function initPlaytimeTransfer() {
    const section = document.getElementById('playtimeTransferSection');
    if (!section || !currentUser?.authenticated) return;

    section.hidden = !canManagePlaytime();
}

async function loadPlaytimeOverview() {
    const result = document.getElementById('playtimeTransferResult');
    const title = document.getElementById('playtimePlayerTitle');
    const toolbar = document.getElementById('playtimeToolbar');
    if (result) result.innerHTML = '';

    const nick = document.getElementById('playtimePlayerNick')?.value.trim() || '';
    if (!nick) {
        alert('Укажите ник игрока');
        return;
    }

    const table = document.getElementById('playtimeRolesTable');
    if (table) table.innerHTML = '<p class="empty-state">Загрузка...</p>';

    try {
        const data = await apiCall('GET', `/api/playtime/overview?player_nick=${encodeURIComponent(nick)}`);
        playtimeOverview = data;
        for (const role of playtimeOverview.roles) {
            role._selected = false;
            role._transferMinutes = '';
            role._hidden = false;
        }

        if (title) {
            title.hidden = false;
            title.innerHTML = `Игрок: <strong>${escapeHtml(data.player_name || nick)}</strong>`;
        }
        if (toolbar) toolbar.hidden = false;
        renderPlaytimeSources();
        renderPlaytimeRolesTable();
    } catch (e) {
        playtimeOverview = null;
        if (table) table.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
        if (toolbar) toolbar.hidden = true;
        document.getElementById('playtimeSourceRow').hidden = true;
    }
}

async function submitPlaytimeBulkTransfer() {
    const result = document.getElementById('playtimeTransferResult');
    const nick = document.getElementById('playtimePlayerNick')?.value.trim() || '';

    try {
        const { fromTracker, transfers } = collectPlaytimeTransfers();
        const data = await apiCall('POST', '/api/playtime/transfer/bulk', {
            player_nick: nick,
            from_tracker: fromTracker,
            transfers,
        });
        const labels = data.transfers.map(t => `${t.to_label} (${t.minutes} м)`).join(', ');
        if (result) {
            result.innerHTML = `<p class="success">Перенесено ${data.total_minutes} мин с «${escapeHtml(data.from_label)}» на: ${escapeHtml(labels)} (${escapeHtml(data.player_name || '')})</p>`;
        }
        await loadPlaytimeOverview();
    } catch (e) {
        if (result) result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function unlockAllPlaytimeRoles() {
    const result = document.getElementById('playtimeTransferResult');
    const nick = document.getElementById('playtimePlayerNick')?.value.trim() || '';
    const fromTracker = document.getElementById('playtimeFromTracker')?.value;

    if (!nick) {
        alert('Укажите ник игрока');
        return;
    }
    if (!fromTracker) {
        alert('Выберите роль, откуда переносить время');
        return;
    }
    if (!confirm('Перенести время на все роли, которым не хватает до разблокировки?')) return;

    try {
        const data = await apiCall('POST', '/api/playtime/unlock-all', {
            player_nick: nick,
            from_tracker: fromTracker,
        });
        if (result) {
            const msg = data.message || 'Готово';
            const detail = data.total_minutes
                ? ` Перенесено ${data.total_minutes} мин с «${data.from_label}».`
                : '';
            result.innerHTML = `<p class="success">${escapeHtml(msg)}${escapeHtml(detail)} (${escapeHtml(data.player_name || '')})</p>`;
        }
        await loadPlaytimeOverview();
    } catch (e) {
        if (result) result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const nickInput = document.getElementById('playtimePlayerNick');
    if (nickInput && !nickInput.dataset.bound) {
        nickInput.dataset.bound = '1';
        nickInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') loadPlaytimeOverview();
        });
    }
    const fromSelect = document.getElementById('playtimeFromTracker');
    if (fromSelect && !fromSelect.dataset.bound) {
        fromSelect.dataset.bound = '1';
        fromSelect.addEventListener('change', () => {
            const fromTracker = fromSelect.value;
            for (const role of playtimeOverview?.roles || []) {
                if (role.tracker === fromTracker) {
                    role._selected = false;
                    role._transferMinutes = '';
                }
            }
            renderPlaytimeRolesTable();
        });
    }
});
