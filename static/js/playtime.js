let playtimeRoleCatalog = [];
let playtimePlayerJobs = [];
let playtimeSelectedFrom = null;
let playtimeSelectedTo = null;

function playtimeJobCard(job, mode, selectedTracker) {
    const selected = selectedTracker === job.tracker ? ` selected-${mode}` : '';
    const timeHtml = job.time_text
        ? `<span class="playtime-job-time">${escapeHtml(job.time_text)}</span>`
        : '';
    const tracker = JSON.stringify(job.tracker);
    return `
        <button type="button"
            class="playtime-job-card${selected}"
            data-tracker="${escapeHtml(job.tracker)}"
            data-mode="${mode}"
            onclick="selectPlaytimeJob(${tracker}, '${mode}')">
            <img src="${escapeHtml(job.icon)}" alt="" class="playtime-job-icon"
                 onerror="this.src='/static/job_icons/Unknown.png'">
            <span class="playtime-job-name">${escapeHtml(job.label)}</span>
            ${timeHtml}
        </button>
    `;
}

function renderPlaytimeFromJobs() {
    const container = document.getElementById('playtimeFromJobs');
    if (!container) return;
    if (!playtimePlayerJobs.length) {
        container.innerHTML = '<p class="empty-state">Нет времени на должностях</p>';
        return;
    }
    container.innerHTML = playtimePlayerJobs.map(j =>
        playtimeJobCard(j, 'from', playtimeSelectedFrom)
    ).join('');
}

function renderPlaytimeToJobs(filter = '') {
    const container = document.getElementById('playtimeToJobs');
    if (!container) return;
    const q = filter.trim().toLowerCase();
    const roles = playtimeRoleCatalog.filter(r =>
        !q || r.label.toLowerCase().includes(q) || r.role_id.toLowerCase().includes(q)
    );
    if (!roles.length) {
        container.innerHTML = '<p class="empty-state">Роль не найдена</p>';
        return;
    }
    container.innerHTML = roles.map(r =>
        playtimeJobCard(r, 'to', playtimeSelectedTo)
    ).join('');
}

function selectPlaytimeJob(tracker, mode) {
    if (mode === 'from') {
        playtimeSelectedFrom = playtimeSelectedFrom === tracker ? null : tracker;
        renderPlaytimeFromJobs();
    } else {
        playtimeSelectedTo = playtimeSelectedTo === tracker ? null : tracker;
        renderPlaytimeToJobs(document.getElementById('playtimeToSearch')?.value || '');
    }
}

function filterPlaytimeToRoles() {
    const q = document.getElementById('playtimeToSearch')?.value || '';
    renderPlaytimeToJobs(q);
}

function setPlaytimeMinutes(value) {
    const input = document.getElementById('playtimeMinutes');
    if (input) input.value = String(value);
}

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
            renderPlaytimeToJobs();
        } catch (e) {
            console.error('playtime roles', e);
        }
    }
    await loadPlaytimeJobs();
}

async function loadPlaytimeJobs() {
    const result = document.getElementById('playtimeTransferResult');
    const title = document.getElementById('playtimePlayerTitle');
    if (result) result.innerHTML = '';

    const nickInput = document.getElementById('playtimePlayerNick');
    const nick = nickInput?.value.trim() || '';
    const canOther = currentUser?.is_time_keeper || currentUser?.is_admin;
    const query = canOther && nick ? `?player_nick=${encodeURIComponent(nick)}` : '';

    const fromContainer = document.getElementById('playtimeFromJobs');
    if (fromContainer) fromContainer.innerHTML = '<p class="empty-state">Загрузка...</p>';

    try {
        const data = await apiCall('GET', `/api/playtime/jobs${query}`);
        playtimePlayerJobs = data.jobs || [];
        playtimeSelectedFrom = null;
        playtimeSelectedTo = null;

        if (title) {
            title.hidden = false;
            title.innerHTML = `Игрок: <strong>${escapeHtml(data.player_name || '—')}</strong>`;
        }
        renderPlaytimeFromJobs();
        renderPlaytimeToJobs(document.getElementById('playtimeToSearch')?.value || '');
    } catch (e) {
        playtimePlayerJobs = [];
        if (fromContainer) fromContainer.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

async function submitPlaytimeTransfer() {
    const result = document.getElementById('playtimeTransferResult');
    const minutes = parseFloat(document.getElementById('playtimeMinutes')?.value || '0');
    const nick = document.getElementById('playtimePlayerNick')?.value.trim() || '';

    if (!playtimeSelectedFrom || !playtimeSelectedTo) {
        alert('Выберите роли: откуда и куда');
        return;
    }
    if (!minutes || minutes <= 0) {
        alert('Укажите количество минут');
        return;
    }

    try {
        const data = await apiCall('POST', '/api/playtime/transfer', {
            player_nick: nick,
            from_tracker: playtimeSelectedFrom,
            to_tracker: playtimeSelectedTo,
            minutes,
        });
        if (result) {
            result.innerHTML = `<p class="success">Перенесено ${data.minutes} мин: ${escapeHtml(data.from_label)} → ${escapeHtml(data.to_label)} (${escapeHtml(data.player_name || '')})</p>`;
        }
        document.getElementById('playtimeMinutes').value = '';
        playtimeSelectedFrom = null;
        playtimeSelectedTo = null;
        await loadPlaytimeJobs();
    } catch (e) {
        if (result) result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const nickInput = document.getElementById('playtimePlayerNick');
    if (nickInput && !nickInput.dataset.bound) {
        nickInput.dataset.bound = '1';
        nickInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') loadPlaytimeJobs();
        });
    }
});
