const SUPPORT_EMAIL_FALLBACK = 'mini-station-14@yandex.ru';

let adminInboxType = 'all';
let adminInboxItems = [];
let adminInboxSelectedKey = null;
let supportOpenTicketId = null;
let supportTicketPollTimer = null;
let adminTicketPollTimer = null;

async function initSupportSection() {
    await loadSupportContacts();
    const wrap = document.getElementById('supportMyTicketsWrap');
    if (currentUser?.authenticated) {
        if (wrap) wrap.hidden = false;
        loadMySupportTickets();
        const contact = document.getElementById('supportContact');
        if (contact && !contact.value) {
            contact.value = currentUser.username || '';
        }
        if (typeof setupChatImagePreview === 'function') {
            setupChatImagePreview('supportChatImage', 'supportChatImagePreview');
        }
    } else if (wrap) {
        wrap.hidden = true;
        closeSupportChat();
    }
}

async function loadSupportContacts() {
    try {
        const data = await apiCall('GET', '/api/support/contacts');
        const email = data.email || SUPPORT_EMAIL_FALLBACK;
        const emailLink = document.getElementById('supportEmailLink');
        if (emailLink) {
            emailLink.href = `mailto:${email}`;
            emailLink.textContent = email;
        }
        const phoneLink = document.getElementById('supportPhoneLink');
        if (phoneLink && (data.phone || data.phone_tel)) {
            phoneLink.href = `tel:${data.phone_tel || String(data.phone).replace(/[^\d+]/g, '')}`;
            phoneLink.textContent = data.phone || data.phone_tel;
        }
        const discordEl = document.getElementById('supportDiscordName');
        if (discordEl && data.discord_username) {
            discordEl.textContent = data.discord_username;
        }
        const tgCard = document.getElementById('supportTelegramCard');
        const tgLink = document.getElementById('supportTelegramLink');
        if (tgCard && tgLink && data.telegram_username) {
            const u = String(data.telegram_username).replace(/^@/, '');
            tgCard.hidden = false;
            tgLink.href = `https://t.me/${encodeURIComponent(u)}`;
            tgLink.textContent = `@${u}`;
        }
    } catch {
        /* keep defaults */
    }
}

async function submitSupportTicket(event) {
    event.preventDefault();
    const result = document.getElementById('supportFormResult');
    const btn = document.getElementById('supportSubmitBtn');
    const contact = document.getElementById('supportContact')?.value.trim() || '';
    const subject = document.getElementById('supportSubject')?.value.trim() || '';
    const body = document.getElementById('supportBody')?.value.trim() || '';
    const formData = new FormData();
    formData.append('contact', contact);
    formData.append('subject', subject);
    formData.append('body', body);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Отправка…';
    }
    try {
        const res = await apiCall('POST', '/api/support/tickets', formData);
        if (result) {
            result.className = 'result success';
            result.textContent = `Тикет #${res.ticket_id} создан`;
        }
        const form = document.getElementById('supportTicketForm');
        if (form) form.reset();
        if (currentUser?.authenticated) {
            const c = document.getElementById('supportContact');
            if (c && currentUser.username) c.value = currentUser.username;
            await loadMySupportTickets();
            if (res.ticket_id) openSupportTicket(res.ticket_id);
        }
    } catch (e) {
        if (result) {
            result.className = 'result error';
            result.textContent = e.message || 'Не удалось отправить';
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-paper-plane" aria-hidden="true"></i> Создать';
        }
    }
}

function ticketStatusMeta(status) {
    const map = {
        open: { label: 'Открыт', icon: 'fa-circle', cls: 'is-open' },
        answered: { label: 'Отвечен', icon: 'fa-reply', cls: 'is-answered' },
        closed: { label: 'Закрыт', icon: 'fa-lock', cls: 'is-closed' },
        pending: { label: 'Ожидает', icon: 'fa-hourglass-half', cls: 'is-open' },
        approved: { label: 'Одобрено', icon: 'fa-check', cls: 'is-answered' },
        rejected: { label: 'Отклонено', icon: 'fa-xmark', cls: 'is-closed' },
    };
    return map[status] || { label: status || '—', icon: 'fa-circle', cls: 'is-closed' };
}

function formatInboxTime(iso) {
    if (!iso) return '';
    try {
        return new Date(iso).toLocaleString('ru-RU', {
            day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
        });
    } catch {
        return String(iso);
    }
}

function formatTicketChatTime(iso) {
    if (!iso) return '';
    try {
        return new Date(iso).toLocaleString('ru-RU', {
            day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
        });
    } catch {
        return String(iso);
    }
}

function renderTicketChatMessage(m, opts = {}) {
    const isStaff = m.author_type === 'staff';
    const own = !isStaff;
    const text = m.content || '';
    const time = formatTicketChatTime(m.created_at);
    const imageHtml = m.image_url && typeof renderChatImage === 'function'
        ? renderChatImage(m.image_url, 'pm-msg-image')
        : (m.image_url ? `<img src="${escapeHtml(m.image_url)}" class="pm-msg-image" alt="">` : '');
    const textHtml = text
        ? `<div class="dc-content">${typeof formatMessageContent === 'function' ? formatMessageContent(text) : escapeHtml(text)}</div>`
        : '';
    const compact = !!opts.compact;
    const name = isStaff
        ? (m.author_name || 'Поддержка')
        : (m.author_name || currentUser?.display_name || currentUser?.username || 'Вы');
    const nameCls = isStaff ? 'dc-name' : 'dc-name dc-name-own';
    const staffBadge = isStaff
        ? '<span class="support-staff-badge">SUPPORT</span>'
        : '';
    const avatarHtml = compact
        ? `<div class="dc-avatar-col" aria-hidden="true"><span class="dc-compact-time">${time}</span></div>`
        : `<div class="dc-avatar-col"><div class="dc-avatar support-chat-avatar ${isStaff ? 'is-staff' : 'is-user'}">${isStaff ? '<i class="fa-solid fa-headset"></i>' : '<i class="fa-solid fa-user"></i>'}</div></div>`;

    if (!textHtml && !imageHtml) return '';

    return `<div class="dc-msg pm-message ${own ? 'own' : 'staff'} ${compact ? 'dc-msg-compact' : ''}">
        ${avatarHtml}
        <div class="dc-body">
            ${compact ? '' : `<div class="dc-header"><span class="${nameCls}">${escapeHtml(name)}</span>${staffBadge}<span class="dc-timestamp">${time}</span></div>`}
            ${textHtml}
            ${imageHtml ? `<div class="dc-attach">${imageHtml}</div>` : ''}
        </div>
    </div>`;
}

function renderTicketMessagesHtml(messages) {
    if (!messages?.length) {
        return '<p class="empty-state">Пока нет сообщений</p>';
    }
    return messages.map((m, i) => {
        const prev = i > 0 ? messages[i - 1] : null;
        const sameAuthor = prev && prev.author_type === m.author_type
            && (prev.author_id || '') === (m.author_id || '');
        const gapMs = prev ? Math.abs(new Date(m.created_at) - new Date(prev.created_at)) : Infinity;
        const compact = sameAuthor && gapMs < 7 * 60 * 1000;
        return renderTicketChatMessage(m, { compact });
    }).join('');
}

async function loadMySupportTickets() {
    const box = document.getElementById('supportMyTickets');
    if (!box || !currentUser?.authenticated) return;
    try {
        const items = await apiCall('GET', '/api/support/tickets/mine');
        if (!items.length) {
            box.innerHTML = '<p class="empty-state">Пока нет обращений</p>';
            return;
        }
        box.innerHTML = items.map(t => {
            const st = ticketStatusMeta(t.status);
            const preview = (t.last_message || t.body || '').slice(0, 80);
            const active = Number(t.id) === Number(supportOpenTicketId) ? ' active' : '';
            return `
            <button type="button" class="support-ticket-card support-ticket-list-item${active}"
                data-ticket-id="${t.id}" onclick="openSupportTicket(${t.id})">
                <header class="support-ticket-card-head">
                    <div>
                        <span class="support-ticket-id">#${t.id}</span>
                        <strong>${escapeHtml(t.subject || 'Без темы')}</strong>
                    </div>
                    <span class="inbox-status-pill ${st.cls}">
                        <i class="fa-solid ${st.icon}" aria-hidden="true"></i>
                        <span>${st.label}</span>
                    </span>
                </header>
                <p class="support-ticket-card-body">${escapeHtml(preview)}${(t.last_message || t.body || '').length > 80 ? '…' : ''}</p>
                <footer class="support-ticket-card-meta">${formatInboxTime(t.last_message_at || t.updated_at || t.created_at)}</footer>
            </button>`;
        }).join('');
    } catch {
        box.innerHTML = '<p class="error">Не удалось загрузить тикеты</p>';
    }
}

function closeSupportChat() {
    supportOpenTicketId = null;
    stopSupportTicketPolling();
    const empty = document.getElementById('supportChatEmpty');
    const shell = document.getElementById('supportChatShell');
    if (empty) empty.hidden = false;
    if (shell) shell.hidden = true;
    document.querySelectorAll('.support-ticket-list-item').forEach(el => el.classList.remove('active'));
}

async function openSupportTicket(ticketId) {
    if (!currentUser?.authenticated) return;
    supportOpenTicketId = Number(ticketId);
    document.querySelectorAll('.support-ticket-list-item').forEach(el => {
        el.classList.toggle('active', Number(el.dataset.ticketId) === supportOpenTicketId);
    });
    const empty = document.getElementById('supportChatEmpty');
    const shell = document.getElementById('supportChatShell');
    if (empty) empty.hidden = true;
    if (shell) shell.hidden = false;
    await refreshSupportChat();
    startSupportTicketPolling();
}

async function refreshSupportChat() {
    if (!supportOpenTicketId) return;
    const box = document.getElementById('supportChatMessages');
    if (!box) return;
    try {
        const data = await apiCall('GET', `/api/support/tickets/${supportOpenTicketId}`);
        const ticket = data.ticket || {};
        const messages = data.messages || [];
        const st = ticketStatusMeta(ticket.status);
        const idEl = document.getElementById('supportChatId');
        const subEl = document.getElementById('supportChatSubject');
        const stEl = document.getElementById('supportChatStatus');
        if (idEl) idEl.textContent = `#${ticket.id}`;
        if (subEl) subEl.textContent = ticket.subject || 'Без темы';
        if (stEl) {
            stEl.className = `inbox-status-pill ${st.cls}`;
            stEl.innerHTML = `<i class="fa-solid ${st.icon}" aria-hidden="true"></i><span>${st.label}</span>`;
        }
        const closed = ticket.status === 'closed';
        const composer = document.getElementById('supportChatComposer');
        const closedHint = document.getElementById('supportChatClosed');
        if (composer) composer.hidden = closed;
        if (closedHint) closedHint.hidden = !closed;

        const wasAtBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 64;
        box.innerHTML = renderTicketMessagesHtml(messages);
        if (wasAtBottom || !box.dataset.ready) {
            box.scrollTop = box.scrollHeight;
            box.dataset.ready = '1';
        }
    } catch (e) {
        box.innerHTML = `<p class="error">${escapeHtml(e.message || 'Ошибка загрузки')}</p>`;
    }
}

async function sendSupportChatMessage() {
    if (!supportOpenTicketId || !currentUser?.authenticated) return;
    const input = document.getElementById('supportChatInput');
    const imageInput = document.getElementById('supportChatImage');
    const content = input?.value.trim() || '';
    const file = imageInput?.files?.[0];
    if (!content && !file) return;

    const formData = new FormData();
    formData.append('content', content);
    if (file) formData.append('image', file);
    try {
        await apiCall('POST', `/api/support/tickets/${supportOpenTicketId}/messages`, formData);
        if (input) input.value = '';
        if (typeof clearChatImagePreview === 'function') {
            clearChatImagePreview('supportChatImage', 'supportChatImagePreview');
        } else if (imageInput) {
            imageInput.value = '';
            const prev = document.getElementById('supportChatImagePreview');
            if (prev) { prev.hidden = true; prev.innerHTML = ''; }
        }
        await refreshSupportChat();
        loadMySupportTickets();
    } catch (e) {
        alert(e.message || 'Не удалось отправить');
    }
}

function startSupportTicketPolling() {
    stopSupportTicketPolling();
    supportTicketPollTimer = setInterval(() => {
        if (supportOpenTicketId) refreshSupportChat();
    }, 5000);
}

function stopSupportTicketPolling() {
    if (supportTicketPollTimer) {
        clearInterval(supportTicketPollTimer);
        supportTicketPollTimer = null;
    }
}

/* ===== Admin unified inbox ===== */

function setAdminInboxType(type, btn) {
    adminInboxType = type || 'active';
    document.querySelectorAll('.inbox-type-btn').forEach(b => {
        const on = b.dataset.inboxType === adminInboxType;
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    if (btn) {
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
    }
    loadAdminInbox();
}

function normalizeTicketItem(t) {
    return {
        key: `ticket-${t.id}`,
        kind: 'ticket',
        id: t.id,
        status: t.status || 'open',
        title: t.subject || 'Без темы',
        body: t.last_message || t.body || '',
        contact: t.contact || '',
        player_id: t.player_id || '',
        admin_response: t.admin_response || '',
        reviewed_by: t.reviewed_by || '',
        created_at: t.last_message_at || t.created_at,
        updated_at: t.updated_at,
    };
}

function normalizeAppealItem(a) {
    return {
        key: `appeal-${a.id}`,
        kind: 'appeal',
        id: a.id,
        status: a.status || 'pending',
        title: `Обжалование бана #${a.ban_id}`,
        body: a.appeal_text || '',
        contact: a.ckey || a.player_id || '',
        player_id: a.player_id || '',
        ban_id: a.ban_id,
        user_uuid: a.user_uuid || '',
        admin_response: a.admin_response || '',
        reviewed_by: a.reviewed_by || '',
        created_at: a.created_at,
        updated_at: a.updated_at,
    };
}

function inboxStatusMatches(item, filter) {
    if (!filter) return true;
    if (filter === 'open') {
        return item.kind === 'ticket'
            ? item.status === 'open'
            : item.status === 'pending';
    }
    if (filter === 'done') {
        return item.kind === 'ticket'
            ? item.status === 'answered' || item.status === 'closed'
            : item.status === 'approved' || item.status === 'rejected';
    }
    return true;
}

async function loadAdminInbox() {
    const list = document.getElementById('adminInboxList');
    const detail = document.getElementById('adminInboxDetail');
    if (!list) return;
    list.innerHTML = '<p class="empty-state">Загрузка...</p>';
    const statusFilter = document.getElementById('adminInboxStatus')?.value ?? '';

    try {
        const fetches = [];
        if (adminInboxType === 'active' || adminInboxType === 'tickets' || adminInboxType === 'all') {
            let tUrl = '/api/admin/support-tickets';
            if (statusFilter === 'open') tUrl += '?status=open';
            fetches.push(apiCall('GET', tUrl).then(rows => (rows || []).map(normalizeTicketItem)).catch(() => []));
        } else {
            fetches.push(Promise.resolve([]));
        }
        if (adminInboxType === 'active' || adminInboxType === 'appeals' || adminInboxType === 'all') {
            let aUrl = '/api/admin/appeals';
            if (statusFilter === 'open') aUrl += '?status=pending';
            fetches.push(apiCall('GET', aUrl).then(rows => (rows || []).map(normalizeAppealItem)).catch(() => []));
        } else {
            fetches.push(Promise.resolve([]));
        }

        const [ticketItems, appealItems] = await Promise.all(fetches);
        let items = [...ticketItems, ...appealItems];
        items = items.filter(i => inboxStatusMatches(i, statusFilter));
        items.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
        adminInboxItems = items;

        if (!items.length) {
            list.innerHTML = '<p class="empty-state">Обращений нет</p>';
            if (detail) {
                detail.innerHTML = `<div class="inbox-detail-empty">
                    <i class="fa-regular fa-envelope-open" aria-hidden="true"></i>
                    <p>Очередь пуста</p>
                </div>`;
            }
            adminInboxSelectedKey = null;
            stopAdminTicketPolling();
            return;
        }

        list.innerHTML = items.map(item => renderInboxListItem(item)).join('');
        if (!list.dataset.boundClick) {
            list.dataset.boundClick = '1';
            list.addEventListener('click', (e) => {
                const btn = e.target.closest('.inbox-list-item');
                if (!btn || !list.contains(btn)) return;
                const key = btn.dataset.key;
                if (key) selectAdminInboxItem(key);
            });
        }
        const keep = items.find(i => i.key === adminInboxSelectedKey) || items[0];
        selectAdminInboxItem(keep.key);
    } catch (e) {
        list.innerHTML = `<p class="error">${escapeHtml(e.message || 'Ошибка загрузки')}</p>`;
    }
}

function renderInboxListItem(item) {
    const st = ticketStatusMeta(item.status);
    const kindLabel = item.kind === 'appeal' ? 'Обжалование' : 'Тикет';
    const kindIcon = item.kind === 'appeal' ? 'fa-gavel' : 'fa-ticket';
    const active = item.key === adminInboxSelectedKey ? ' active' : '';
    const preview = (item.body || '').slice(0, 90);
    return `
        <button type="button" class="inbox-list-item${active}" role="option"
            aria-selected="${active ? 'true' : 'false'}"
            data-key="${escapeHtml(item.key)}">
            <div class="inbox-list-item-top">
                <span class="inbox-kind-chip">
                    <i class="fa-solid ${kindIcon}" aria-hidden="true"></i>
                    ${kindLabel}
                </span>
                <span class="inbox-status-pill ${st.cls}">
                    <i class="fa-solid ${st.icon}" aria-hidden="true"></i>
                    <span>${st.label}</span>
                </span>
            </div>
            <div class="inbox-list-item-title">#${item.id} · ${escapeHtml(item.title)}</div>
            <div class="inbox-list-item-preview">${escapeHtml(preview)}${(item.body || '').length > 90 ? '…' : ''}</div>
            <div class="inbox-list-item-meta">${formatInboxTime(item.created_at)}</div>
        </button>`;
}

function selectAdminInboxItem(key) {
    adminInboxSelectedKey = key;
    const item = adminInboxItems.find(i => i.key === key);
    document.querySelectorAll('.inbox-list-item').forEach(el => {
        const on = el.dataset.key === key;
        el.classList.toggle('active', on);
        el.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    const detail = document.getElementById('adminInboxDetail');
    if (!detail) return;
    if (!item) {
        stopAdminTicketPolling();
        detail.innerHTML = `<div class="inbox-detail-empty">
            <i class="fa-regular fa-envelope-open" aria-hidden="true"></i>
            <p>Выберите обращение слева</p>
        </div>`;
        return;
    }
    if (item.kind === 'appeal') {
        stopAdminTicketPolling();
        detail.innerHTML = renderAppealDetail(item);
        return;
    }
    detail.innerHTML = renderTicketDetailChat(item);
    if (typeof setupChatImagePreview === 'function') {
        setupChatImagePreview('adminTicketImage', 'adminTicketImagePreview');
    }
    refreshAdminTicketChat(item.id);
    startAdminTicketPolling(item.id);
}

function renderTicketDetailChat(item) {
    const st = ticketStatusMeta(item.status);
    return `
        <article class="inbox-detail-card inbox-ticket-chat">
            <header class="inbox-detail-head">
                <div>
                    <span class="inbox-kind-chip"><i class="fa-solid fa-ticket" aria-hidden="true"></i> Тикет #${item.id}</span>
                    <h3>${escapeHtml(item.title)}</h3>
                </div>
                <span class="inbox-status-pill ${st.cls}" id="adminTicketStatusPill">
                    <i class="fa-solid ${st.icon}" aria-hidden="true"></i>
                    <span>${st.label}</span>
                </span>
            </header>
            <dl class="inbox-meta-grid">
                <div><dt>Контакт</dt><dd>${escapeHtml(item.contact || '—')}</dd></div>
                <div><dt>Игрок</dt><dd>${escapeHtml(item.player_id || 'гость')}</dd></div>
                <div><dt>Создан</dt><dd>${formatInboxTime(item.created_at)}</dd></div>
            </dl>
            <div class="dc-messages support-chat-messages admin-ticket-messages" id="adminTicketMessages">
                <p class="empty-state">Загрузка...</p>
            </div>
            <div class="chat-composer dc-composer support-chat-composer" id="adminTicketComposer">
                <div class="chat-composer-tools">
                    <label class="chat-tool-btn" title="Изображение">
                        <i class="fa-solid fa-image"></i>
                        <input type="file" id="adminTicketImage" accept="image/*" hidden>
                    </label>
                </div>
                <div class="chat-composer-main">
                    <textarea id="adminTicketInput" rows="1" maxlength="4000"
                        placeholder="Ответ поддержки..."
                        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendAdminTicketMessage(${item.id});}"></textarea>
                    <div id="adminTicketImagePreview" class="chat-image-preview" hidden></div>
                </div>
                <button type="button" class="chat-send-btn" onclick="sendAdminTicketMessage(${item.id})" title="Отправить">
                    <i class="fa-solid fa-paper-plane"></i>
                </button>
            </div>
            <div class="inbox-reply-actions admin-ticket-status-row">
                <label for="adminTicketStatus">Статус</label>
                <select id="adminTicketStatus">
                    <option value="open" ${item.status === 'open' ? 'selected' : ''}>Открыт</option>
                    <option value="answered" ${item.status === 'answered' ? 'selected' : ''}>Отвечен</option>
                    <option value="closed" ${item.status === 'closed' ? 'selected' : ''}>Закрыт</option>
                </select>
                <button type="button" class="inbox-btn-primary" onclick="saveAdminTicketStatus(${item.id})">
                    Сохранить статус
                </button>
            </div>
            <div id="inboxReplyResult" class="result" role="status" aria-live="polite"></div>
        </article>`;
}

async function refreshAdminTicketChat(ticketId) {
    const box = document.getElementById('adminTicketMessages');
    if (!box) return;
    try {
        const data = await apiCall('GET', `/api/admin/support-tickets/${ticketId}`);
        const messages = data.messages || [];
        const ticket = data.ticket || {};
        const wasAtBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 64;
        box.innerHTML = renderTicketMessagesHtml(messages);
        if (wasAtBottom || !box.dataset.ready) {
            box.scrollTop = box.scrollHeight;
            box.dataset.ready = '1';
        }
        const st = ticketStatusMeta(ticket.status);
        const pill = document.getElementById('adminTicketStatusPill');
        if (pill) {
            pill.className = `inbox-status-pill ${st.cls}`;
            pill.innerHTML = `<i class="fa-solid ${st.icon}" aria-hidden="true"></i><span>${st.label}</span>`;
        }
        const sel = document.getElementById('adminTicketStatus');
        if (sel && ticket.status) sel.value = ticket.status;
    } catch (e) {
        box.innerHTML = `<p class="error">${escapeHtml(e.message || 'Ошибка')}</p>`;
    }
}

async function sendAdminTicketMessage(ticketId) {
    const input = document.getElementById('adminTicketInput');
    const imageInput = document.getElementById('adminTicketImage');
    const content = input?.value.trim() || '';
    const file = imageInput?.files?.[0];
    if (!content && !file) return;
    const status = document.getElementById('adminTicketStatus')?.value || 'answered';
    const formData = new FormData();
    formData.append('content', content);
    formData.append('status', status);
    if (file) formData.append('image', file);
    const result = document.getElementById('inboxReplyResult');
    try {
        await apiCall('POST', `/api/admin/support-tickets/${ticketId}/messages`, formData);
        if (input) input.value = '';
        if (typeof clearChatImagePreview === 'function') {
            clearChatImagePreview('adminTicketImage', 'adminTicketImagePreview');
        } else if (imageInput) {
            imageInput.value = '';
            const prev = document.getElementById('adminTicketImagePreview');
            if (prev) { prev.hidden = true; prev.innerHTML = ''; }
        }
        if (result) {
            result.className = 'result success';
            result.textContent = 'Отправлено';
        }
        await refreshAdminTicketChat(ticketId);
        await loadAdminInbox();
    } catch (e) {
        if (result) {
            result.className = 'result error';
            result.textContent = e.message || 'Ошибка';
        }
    }
}

async function saveAdminTicketStatus(ticketId) {
    const status = document.getElementById('adminTicketStatus')?.value || 'answered';
    const result = document.getElementById('inboxReplyResult');
    try {
        await apiCall('POST', `/api/admin/support-tickets/${ticketId}/status`, { status, admin_response: '' });
        if (result) {
            result.className = 'result success';
            result.textContent = 'Статус обновлён';
        }
        await loadAdminInbox();
    } catch (e) {
        if (result) {
            result.className = 'result error';
            result.textContent = e.message || 'Ошибка';
        }
    }
}

function startAdminTicketPolling(ticketId) {
    stopAdminTicketPolling();
    adminTicketPollTimer = setInterval(() => {
        if (adminInboxSelectedKey === `ticket-${ticketId}`) {
            refreshAdminTicketChat(ticketId);
        }
    }, 5000);
}

function stopAdminTicketPolling() {
    if (adminTicketPollTimer) {
        clearInterval(adminTicketPollTimer);
        adminTicketPollTimer = null;
    }
}

function renderAppealDetail(item) {
    const st = ticketStatusMeta(item.status);
    const canReview = item.status === 'pending';
    return `
        <article class="inbox-detail-card">
            <header class="inbox-detail-head">
                <div>
                    <span class="inbox-kind-chip"><i class="fa-solid fa-gavel" aria-hidden="true"></i> Обжалование #${item.id}</span>
                    <h3>${escapeHtml(item.title)}</h3>
                </div>
                <span class="inbox-status-pill ${st.cls}">
                    <i class="fa-solid ${st.icon}" aria-hidden="true"></i>
                    <span>${st.label}</span>
                </span>
            </header>
            <dl class="inbox-meta-grid">
                <div><dt>Бан</dt><dd>#${item.ban_id}</dd></div>
                <div><dt>Игрок</dt><dd>${escapeHtml(item.player_id || '—')}</dd></div>
                <div><dt>Сикей</dt><dd>${escapeHtml(item.contact || '—')}</dd></div>
                <div><dt>Создано</dt><dd>${formatInboxTime(item.created_at)}</dd></div>
                ${item.reviewed_by ? `<div><dt>Рассмотрел</dt><dd>${escapeHtml(item.reviewed_by)}</dd></div>` : ''}
            </dl>
            <section class="inbox-detail-body">
                <h4>Текст обжалования</h4>
                <p>${escapeHtml(item.body)}</p>
            </section>
            ${item.admin_response ? `
                <section class="inbox-detail-reply-prev">
                    <h4>Ответ администрации</h4>
                    <p>${escapeHtml(item.admin_response)}</p>
                </section>` : ''}
            ${canReview ? `
            <form class="inbox-reply-form" onsubmit="submitAppealReply(event, ${item.id})">
                <label for="inboxAppealComment">Комментарий</label>
                <textarea id="inboxAppealComment" rows="3" maxlength="2000"
                    placeholder="Комментарий к решению (необязательно)…"></textarea>
                <div class="inbox-reply-actions">
                    <button type="button" class="inbox-btn-success" onclick="submitAppealDecision(${item.id}, 'approved')">
                        <i class="fa-solid fa-check" aria-hidden="true"></i> Одобрить и снять бан
                    </button>
                    <button type="button" class="inbox-btn-danger" onclick="submitAppealDecision(${item.id}, 'rejected')">
                        <i class="fa-solid fa-xmark" aria-hidden="true"></i> Отклонить
                    </button>
                </div>
                <div id="inboxReplyResult" class="result" role="status" aria-live="polite"></div>
            </form>` : `
            <p class="admin-hint">Обжалование уже рассмотрено.</p>`}
        </article>`;
}

async function submitAppealDecision(id, status) {
    const comment = document.getElementById('inboxAppealComment')?.value || '';
    const result = document.getElementById('inboxReplyResult');
    const msg = status === 'approved'
        ? 'Одобрить обжалование и снять бан в игровой БД?'
        : 'Отклонить обжалование?';
    if (!confirm(msg)) return;
    try {
        await apiCall('POST', `/api/admin/appeals/${id}/review`, { status, admin_response: comment });
        if (result) {
            result.className = 'result success';
            result.textContent = status === 'approved' ? 'Одобрено, бан снят' : 'Отклонено';
        }
        await loadAdminInbox();
    } catch (e) {
        if (result) {
            result.className = 'result error';
            result.textContent = e.message || 'Ошибка';
        } else {
            alert(e.message || 'Ошибка');
        }
    }
}

function submitAppealReply(event) {
    event.preventDefault();
}

/* legacy aliases */
async function loadAdminSupportTickets() { return loadAdminInbox(); }
async function loadAdminAppeals() { return loadAdminInbox(); }
async function reviewSupportTicket(id) {
    const status = document.getElementById(`supportStatus_${id}`)?.value || 'answered';
    const admin_response = document.getElementById(`supportReply_${id}`)?.value || '';
    await apiCall('POST', `/api/admin/support-tickets/${id}/review`, { status, admin_response });
    loadAdminInbox();
}
async function submitTicketReply(event, id) {
    event.preventDefault();
    return sendAdminTicketMessage(id);
}
