let playtimeOverview = null;
let playtimeRoleFilter = '';
let playtimeRoleCatalog = [];
let playtimePlayerSearchTimeout = null;
let playtimeRoleSuggestIndex = -1;
let playtimePlayerSuggestIndex = -1;

function canManagePlaytime() {
    return !!(currentUser?.is_time_keeper || currentUser?.is_admin);
}

function playtimeMatchRole(role, query) {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    const trackerName = (role.tracker || role.id || '').replace(/^Job/, '').toLowerCase();
    return (
        (role.label || '').toLowerCase().includes(q)
        || (role.role_id || '').toLowerCase().includes(q)
        || trackerName.includes(q)
        || (role.unlock_hint || '').toLowerCase().includes(q)
        || (role.department_label || '').toLowerCase().includes(q)
        || (role.department || '').toLowerCase().includes(q)
    );
}

function playtimeRoleRow(role) {
    const checked = role._selected ? ' checked' : '';
    const minutes = role._transferMinutes ?? '';
    const unlocked = role.unlocked === true
        ? '<span class="playtime-unlocked-badge">открыта</span>'
        : role.unlocked === false
            ? `<span class="playtime-deficit" title="${escapeHtml(role.unlock_hint || '')}">−${role.deficit_minutes} м</span>`
            : '<span class="playtime-deficit">—</span>';
    const trackerAttr = escapeHtml(role.tracker).replace(/'/g, "\\'");
    return `
        <tr class="playtime-role-row${role._hidden ? ' hidden' : ''}" data-tracker="${escapeHtml(role.tracker)}" id="playtime-row-${escapeHtml(role.role_id)}">
            <td class="playtime-col-check">
                <input type="checkbox" class="playtime-role-check"${checked}
                    onchange="togglePlaytimeRole('${trackerAttr}', this.checked)">
            </td>
            <td class="playtime-col-icon">
                <img src="${escapeHtml(role.icon)}" alt="" class="playtime-job-icon"
                     onerror="this.src='/static/job_icons/Unknown.png'">
            </td>
            <td class="playtime-col-name">
                <span class="playtime-role-label">${escapeHtml(role.label)}</span>
                <span class="playtime-role-id">${escapeHtml(role.role_id)}</span>
            </td>
            <td class="playtime-col-current">${escapeHtml(role.time_text)}</td>
            <td class="playtime-col-status">${unlocked}</td>
            <td class="playtime-col-transfer">
                <input type="number" class="playtime-role-minutes" min="0" step="1"
                    value="${minutes}" placeholder="0"
                    oninput="setPlaytimeRoleMinutes('${trackerAttr}', this.value)">
            </td>
        </tr>
    `;
}

function buildPlaytimeTableBody() {
    let lastDept = null;
    let html = '';
    for (const role of playtimeOverview.roles) {
        if (role._hidden) continue;
        if (role.department !== lastDept) {
            lastDept = role.department;
            html += `
                <tr class="playtime-dept-header">
                    <td colspan="6">${escapeHtml(role.department_label || role.department || 'Прочие')}</td>
                </tr>`;
        }
        html += playtimeRoleRow(role);
    }
    if (!html) {
        html = '<tr><td colspan="6" class="playtime-empty-filter">Нет ролей по фильтру</td></tr>';
    }
    return html;
}

function buildCatalogOverview(catalog) {
    return {
        roles: catalog.map(r => ({
            ...r,
            tracker: r.id || r.tracker,
            minutes: 0,
            time_text: '—',
            unlocked: null,
            deficit_minutes: 0,
            unlock_hint: '',
            department: r.department || '_other',
            department_label: r.department_label || 'Прочие',
            _selected: false,
            _transferMinutes: '',
            _hidden: false,
        })),
        sources: [],
    };
}

function renderPlaytimeRolesTable() {
    const container = document.getElementById('playtimeRolesTable');
    if (!container || !playtimeOverview?.roles?.length) {
        if (container) container.innerHTML = '<p class="empty-state">Загрузка списка ролей...</p>';
        return;
    }

    const q = playtimeRoleFilter.trim().toLowerCase();
    for (const role of playtimeOverview.roles) {
        role._hidden = !!(q && !playtimeMatchRole(role, q));
    }

    const visible = playtimeOverview.roles.filter(r => !r._hidden);
    const totalSelected = visible.filter(r => r._selected).length;
    const selectAll = document.getElementById('playtimeSelectAll');
    if (selectAll) {
        selectAll.indeterminate = totalSelected > 0 && totalSelected < visible.length;
        selectAll.checked = visible.length > 0 && totalSelected === visible.length;
    }

    const playerLoaded = playtimeOverview.player_loaded;
    container.innerHTML = `
        <p class="playtime-roles-count">Ролей: ${playtimeOverview.roles.length}${q ? ` · показано ${visible.length}` : ''}${playerLoaded ? '' : ' · укажите игрока и нажмите «Загрузить»'}</p>
        <div class="playtime-roles-table-scroll">
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
                    ${buildPlaytimeTableBody()}
                </tbody>
            </table>
        </div>
        <p class="playtime-unlock-hint">Требования из билда <a href="https://github.com/ministation/mini-station-goob" target="_blank" rel="noopener">mini-station-goob</a>. Наведите на «−N м» для условия.</p>
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
    renderPlaytimeRolesTable();
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
    renderPlaytimeRoleSuggestions();
}

function getPlaytimeRoleSearchPool() {
    if (playtimeOverview?.roles?.length) return playtimeOverview.roles;
    return playtimeRoleCatalog.map(r => ({
        ...r,
        tracker: r.id || r.tracker,
        time_text: '—',
        unlocked: null,
        deficit_minutes: 0,
        unlock_hint: '',
    }));
}

function renderPlaytimeRoleSuggestions() {
    const input = document.getElementById('playtimeRoleSearch');
    const box = document.getElementById('playtimeRoleSuggestions');
    if (!input || !box) return;

    const q = input.value.trim();
    if (q.length < 1) {
        box.hidden = true;
        box.innerHTML = '';
        playtimeRoleSuggestIndex = -1;
        return;
    }

    const matches = getPlaytimeRoleSearchPool()
        .filter(r => playtimeMatchRole(r, q))
        .slice(0, 12);

    if (!matches.length) {
        box.hidden = false;
        box.innerHTML = '<p class="playtime-suggestion-empty">Роль не найдена</p>';
        return;
    }

    box.hidden = false;
    box.innerHTML = matches.map((role, index) => {
        const hint = role.unlock_hint && role.unlock_hint !== 'без ограничений'
            ? role.unlock_hint
            : (role.unlocked === false ? `не хватает ${role.deficit_minutes} м` : '');
        return `
            <button type="button" class="playtime-suggestion-item${index === playtimeRoleSuggestIndex ? ' active' : ''}"
                onclick="selectPlaytimeRoleSuggestion('${escapeHtml(role.role_id)}')">
                <img src="${escapeHtml(role.icon)}" alt="" class="playtime-job-icon"
                     onerror="this.src='/static/job_icons/Unknown.png'">
                <span class="playtime-suggestion-text">
                    <strong>${escapeHtml(role.label)}</strong>
                    <small>${escapeHtml(role.role_id)}${hint ? ' · ' + escapeHtml(hint) : ''}</small>
                </span>
            </button>`;
    }).join('');
}

function selectPlaytimeRoleSuggestion(roleId) {
    const pool = getPlaytimeRoleSearchPool();
    const role = pool.find(r => r.role_id === roleId);
    if (!role) return;
    const input = document.getElementById('playtimeRoleSearch');
    if (input) input.value = role.label;
    playtimeRoleFilter = role.label;
    renderPlaytimeRoleSuggestions();
    renderPlaytimeRolesTable();
    hidePlaytimeRoleSuggestions();
    const row = document.getElementById(`playtime-row-${roleId}`);
    if (row) {
        row.classList.add('playtime-role-row-highlight');
        row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        setTimeout(() => row.classList.remove('playtime-role-row-highlight'), 2000);
    }
}

function hidePlaytimeRoleSuggestions() {
    const box = document.getElementById('playtimeRoleSuggestions');
    if (box) {
        box.hidden = true;
        box.innerHTML = '';
    }
    playtimeRoleSuggestIndex = -1;
}

function onPlaytimeRoleSearchInput() {
    filterPlaytimeRoles();
}

function onPlaytimeRoleSearchKeydown(event) {
    const box = document.getElementById('playtimeRoleSuggestions');
    const items = box ? [...box.querySelectorAll('.playtime-suggestion-item')] : [];
    if (!items.length) {
        if (event.key === 'Enter') {
            event.preventDefault();
            filterPlaytimeRoles();
        }
        return;
    }
    if (event.key === 'ArrowDown') {
        event.preventDefault();
        playtimeRoleSuggestIndex = Math.min(playtimeRoleSuggestIndex + 1, items.length - 1);
        renderPlaytimeRoleSuggestions();
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        playtimeRoleSuggestIndex = Math.max(playtimeRoleSuggestIndex - 1, 0);
        renderPlaytimeRoleSuggestions();
    } else if (event.key === 'Enter' && playtimeRoleSuggestIndex >= 0) {
        event.preventDefault();
        items[playtimeRoleSuggestIndex]?.click();
    } else if (event.key === 'Escape') {
        hidePlaytimeRoleSuggestions();
    }
}

function debouncePlaytimePlayerSearch() {
    clearTimeout(playtimePlayerSearchTimeout);
    playtimePlayerSearchTimeout = setTimeout(searchPlaytimePlayers, 250);
}

async function searchPlaytimePlayers() {
    const input = document.getElementById('playtimePlayerNick');
    const box = document.getElementById('playtimePlayerSuggestions');
    const q = input?.value.trim() || '';
    if (!box) return;
    if (q.length < 2) {
        box.hidden = true;
        box.innerHTML = '';
        return;
    }
    box.hidden = false;
    box.innerHTML = '<p class="playtime-suggestion-empty">Поиск...</p>';
    try {
        const players = await apiCall('GET', `/api/playtime/players/search?q=${encodeURIComponent(q)}`);
        if (!players.length) {
            box.innerHTML = '<p class="playtime-suggestion-empty">Игроки не найдены</p>';
            return;
        }
        box.innerHTML = players.slice(0, 10).map((p, index) => {
            const name = p.name || p.last_seen_user_name || p.ckey || '—';
            return `
                <button type="button" class="playtime-suggestion-item${index === playtimePlayerSuggestIndex ? ' active' : ''}"
                    onclick="selectPlaytimePlayerSuggestion(${JSON.stringify(name)})">
                    <i class="fa-solid fa-user playtime-suggestion-icon-fa"></i>
                    <span class="playtime-suggestion-text">
                        <strong>${escapeHtml(name)}</strong>
                        <small>${escapeHtml((p.user_uuid || '').slice(0, 8))}…</small>
                    </span>
                </button>`;
        }).join('');
    } catch (e) {
        box.innerHTML = `<p class="playtime-suggestion-empty">${escapeHtml(e.message)}</p>`;
    }
}

function selectPlaytimePlayerSuggestion(nick) {
    const input = document.getElementById('playtimePlayerNick');
    if (input) input.value = nick;
    hidePlaytimePlayerSuggestions();
    loadPlaytimeOverview();
}

function hidePlaytimePlayerSuggestions() {
    const box = document.getElementById('playtimePlayerSuggestions');
    if (box) {
        box.hidden = true;
        box.innerHTML = '';
    }
    playtimePlayerSuggestIndex = -1;
}

function onPlaytimePlayerSearchKeydown(event) {
    const box = document.getElementById('playtimePlayerSuggestions');
    const items = box ? [...box.querySelectorAll('.playtime-suggestion-item')] : [];
    if (event.key === 'ArrowDown' && items.length) {
        event.preventDefault();
        playtimePlayerSuggestIndex = Math.min(playtimePlayerSuggestIndex + 1, items.length - 1);
        searchPlaytimePlayers();
    } else if (event.key === 'ArrowUp' && items.length) {
        event.preventDefault();
        playtimePlayerSuggestIndex = Math.max(playtimePlayerSuggestIndex - 1, 0);
        searchPlaytimePlayers();
    } else if (event.key === 'Enter') {
        event.preventDefault();
        if (playtimePlayerSuggestIndex >= 0 && items[playtimePlayerSuggestIndex]) {
            items[playtimePlayerSuggestIndex].click();
        } else {
            hidePlaytimePlayerSuggestions();
            loadPlaytimeOverview();
        }
    } else if (event.key === 'Escape') {
        hidePlaytimePlayerSuggestions();
    }
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

async function ensurePlaytimeRoleCatalog() {
    if (playtimeRoleCatalog.length) return;
    try {
        playtimeRoleCatalog = await apiCall('GET', '/api/playtime/roles');
    } catch (e) {
        console.error('playtime roles catalog', e);
    }
}

async function initPlaytimeTransfer() {
    if (!canManagePlaytime()) return;
    await ensurePlaytimeRoleCatalog();
    const toolbar = document.getElementById('playtimeToolbar');
    if (toolbar) toolbar.hidden = false;
    if (!playtimeOverview && playtimeRoleCatalog.length) {
        playtimeOverview = buildCatalogOverview(playtimeRoleCatalog);
        playtimeOverview.player_loaded = false;
        renderPlaytimeRolesTable();
    }
}

async function loadPlaytimeOverview() {
    const result = document.getElementById('playtimeTransferResult');
    const title = document.getElementById('playtimePlayerTitle');
    const toolbar = document.getElementById('playtimeToolbar');
    if (result) result.innerHTML = '';
    hidePlaytimePlayerSuggestions();

    const nick = document.getElementById('playtimePlayerNick')?.value.trim() || '';
    if (!nick) {
        alert('Укажите ник игрока');
        return;
    }

    const table = document.getElementById('playtimeRolesTable');
    if (table) table.innerHTML = '<p class="empty-state">Загрузка...</p>';

    try {
        const data = await apiCall('GET', `/api/playtime/overview?player_nick=${encodeURIComponent(nick)}`);
        const prevSelected = new Map(
            (playtimeOverview?.roles || [])
                .filter(r => r._selected || r._transferMinutes)
                .map(r => [r.tracker, { selected: r._selected, minutes: r._transferMinutes }])
        );
        playtimeOverview = data;
        playtimeOverview.player_loaded = true;
        for (const role of playtimeOverview.roles) {
            const prev = prevSelected.get(role.tracker);
            role._selected = prev?.selected || false;
            role._transferMinutes = prev?.minutes || '';
            role._hidden = false;
        }

        if (title) {
            title.hidden = false;
            title.innerHTML = `Игрок: <strong>${escapeHtml(data.player_name || nick)}</strong> · ролей в списке: ${playtimeOverview.roles.length}`;
        }
        if (toolbar) toolbar.hidden = false;
        renderPlaytimeSources();
        renderPlaytimeRolesTable();
    } catch (e) {
        playtimeOverview = null;
        if (table) table.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
        if (toolbar) toolbar.hidden = true;
        const sourceRow = document.getElementById('playtimeSourceRow');
        if (sourceRow) sourceRow.hidden = true;
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

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.playtime-search-wrap')) {
            hidePlaytimeRoleSuggestions();
            hidePlaytimePlayerSuggestions();
        }
    });
});
