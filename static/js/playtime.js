let playtimeRoleCatalog = [];

async function initPlaytimeTransfer() {
    const section = document.getElementById('playtimeTransferSection');
    if (!section || !currentUser?.authenticated) return;

    const canUse = currentUser.player || currentUser.is_time_keeper || currentUser.is_admin;
    section.hidden = !canUse;
    if (!canUse) return;

    const keeperFields = document.getElementById('playtimeKeeperFields');
    if (keeperFields) {
        keeperFields.hidden = !(currentUser.is_time_keeper || currentUser.is_admin);
    }

    if (!playtimeRoleCatalog.length) {
        try {
            playtimeRoleCatalog = await apiCall('GET', '/api/playtime/roles');
            fillPlaytimeRoleSelects();
        } catch (e) {
            console.error('playtime roles', e);
        }
    }
    await loadPlaytimeJobs();
}

function fillPlaytimeRoleSelects() {
    const from = document.getElementById('playtimeFromRole');
    const to = document.getElementById('playtimeToRole');
    if (!from || !to) return;
    const options = playtimeRoleCatalog.map(r =>
        `<option value="${escapeHtml(r.id)}">${escapeHtml(r.label)}</option>`
    ).join('');
    from.innerHTML = `<option value="">— выберите —</option>${options}`;
    to.innerHTML = `<option value="">— выберите —</option>${options}`;
}

async function loadPlaytimeJobs() {
    const list = document.getElementById('playtimeJobsList');
    const result = document.getElementById('playtimeTransferResult');
    if (!list) return;
    if (result) result.innerHTML = '';

    const nickInput = document.getElementById('playtimePlayerNick');
    const nick = nickInput?.value.trim() || '';
    const canOther = currentUser?.is_time_keeper || currentUser?.is_admin;
    const query = canOther && nick ? `?player_nick=${encodeURIComponent(nick)}` : '';

    list.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const data = await apiCall('GET', `/api/playtime/jobs${query}`);
        if (!data.jobs?.length) {
            list.innerHTML = '<p class="empty-state">Нет времени на должностях Job:</p>';
            return;
        }
        list.innerHTML = `
            <p class="playtime-player-title">Игрок: <strong>${escapeHtml(data.player_name || '—')}</strong></p>
            <div class="playtime-jobs-grid">
                ${data.jobs.map(j => `
                    <div class="playtime-job-card">
                        <div class="playtime-job-name">${escapeHtml(j.label)}</div>
                        <div class="playtime-job-hours">${j.hours} ч</div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (e) {
        list.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function submitPlaytimeTransfer() {
    const result = document.getElementById('playtimeTransferResult');
    const fromTracker = document.getElementById('playtimeFromRole')?.value;
    const toTracker = document.getElementById('playtimeToRole')?.value;
    const minutes = parseFloat(document.getElementById('playtimeMinutes')?.value || '0');
    const nick = document.getElementById('playtimePlayerNick')?.value.trim() || '';

    if (!fromTracker || !toTracker) {
        alert('Выберите должности');
        return;
    }
    if (!minutes || minutes <= 0) {
        alert('Укажите количество минут');
        return;
    }

    try {
        const data = await apiCall('POST', '/api/playtime/transfer', {
            player_nick: nick,
            from_tracker: fromTracker,
            to_tracker: toTracker,
            minutes,
        });
        if (result) {
            result.innerHTML = `<p class="success">Перенесено ${data.minutes} мин: ${escapeHtml(data.from_label)} → ${escapeHtml(data.to_label)} (${escapeHtml(data.player_name || '')})</p>`;
        }
        document.getElementById('playtimeMinutes').value = '';
        await loadPlaytimeJobs();
    } catch (e) {
        if (result) result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const nickInput = document.getElementById('playtimePlayerNick');
    if (nickInput && !nickInput.dataset.bound) {
        nickInput.dataset.bound = '1';
        nickInput.addEventListener('change', () => loadPlaytimeJobs());
    }
});
