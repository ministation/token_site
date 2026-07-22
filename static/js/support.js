const SUPPORT_EMAIL_FALLBACK = 'mini-station-14@yandex.ru';

let adminInboxType = 'all';
let adminInboxItems = [];
let adminInboxSelectedKey = null;

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
    } else if (wrap) {
        wrap.hidden = true;
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
            result.textContent = `Тикет #${res.ticket_id} отправлен. Ответим на указанный контакт.`;
        }
        const form = document.getElementById('supportTicketForm');
        if (form) form.reset();
        if (currentUser?.authenticated) {
            const c = document.getElementById('supportContact');
            if (c && currentUser.username) c.value = currentUser.username;
            loadMySupportTickets();
        }
    } catch (e) {
        if (result) {
            result.className = 'result error';
            result.textContent = e.message || 'Не удалось отправить';
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-paper-plane" aria-hidden="true"></i> Отправить тикет';
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
            return `
            <article class="support-ticket-card">
                <header class="support-ticket-card-head">
                    <div>
                        <span class="support-ticket-id">#${t.id}</span>
                        <strong>${escapeHtml(t.subject || 'Без темы')}</strong>
                    </div>
                    <span class="inbox-status-pill ${st.cls}" title="${st.label}">
                        <i class="fa-solid ${st.icon}" aria-hidden="true"></i>
                        <span>${st.label}</span>
                    </span>
                </header>
                <p class="support-ticket-card-body">${escapeHtml(t.body || '')}</p>
                ${t.admin_response ? `
                    <div class="support-ticket-card-reply">
                        <strong><i class="fa-solid fa-headset" aria-hidden="true"></i> Ответ поддержки</strong>
                        <p>${escapeHtml(t.admin_response)}</p>
                    </div>` : ''}
                <footer class="support-ticket-card-meta">${formatInboxTime(t.created_at)}</footer>
            </article>`;
        }).join('');
    } catch {
        box.innerHTML = '<p class="error">Не удалось загрузить тикеты</p>';
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
        body: t.body || '',
        contact: t.contact || '',
        player_id: t.player_id || '',
        admin_response: t.admin_response || '',
        reviewed_by: t.reviewed_by || '',
        created_at: t.created_at,
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
        detail.innerHTML = `<div class="inbox-detail-empty">
            <i class="fa-regular fa-envelope-open" aria-hidden="true"></i>
            <p>Выберите обращение слева</p>
        </div>`;
        return;
    }
    detail.innerHTML = item.kind === 'appeal'
        ? renderAppealDetail(item)
        : renderTicketDetail(item);
}

function renderTicketDetail(item) {
    const st = ticketStatusMeta(item.status);
    return `
        <article class="inbox-detail-card">
            <header class="inbox-detail-head">
                <div>
                    <span class="inbox-kind-chip"><i class="fa-solid fa-ticket" aria-hidden="true"></i> Тикет #${item.id}</span>
                    <h3>${escapeHtml(item.title)}</h3>
                </div>
                <span class="inbox-status-pill ${st.cls}">
                    <i class="fa-solid ${st.icon}" aria-hidden="true"></i>
                    <span>${st.label}</span>
                </span>
            </header>
            <dl class="inbox-meta-grid">
                <div><dt>Контакт</dt><dd>${escapeHtml(item.contact || '—')}</dd></div>
                <div><dt>Игрок</dt><dd>${escapeHtml(item.player_id || 'гость')}</dd></div>
                <div><dt>Создан</dt><dd>${formatInboxTime(item.created_at)}</dd></div>
                ${item.reviewed_by ? `<div><dt>Ответил</dt><dd>${escapeHtml(item.reviewed_by)}</dd></div>` : ''}
            </dl>
            <section class="inbox-detail-body">
                <h4>Сообщение</h4>
                <p>${escapeHtml(item.body)}</p>
            </section>
            ${item.admin_response ? `
                <section class="inbox-detail-reply-prev">
                    <h4>Предыдущий ответ</h4>
                    <p>${escapeHtml(item.admin_response)}</p>
                </section>` : ''}
            <form class="inbox-reply-form" onsubmit="submitTicketReply(event, ${item.id})">
                <label for="inboxReplyText">Ответ поддержки</label>
                <textarea id="inboxReplyText" rows="4" required maxlength="4000"
                    placeholder="Текст ответа пользователю…">${escapeHtml(item.admin_response || '')}</textarea>
                <label for="inboxReplyStatus">Новый статус</label>
                <select id="inboxReplyStatus">
                    <option value="answered" ${item.status === 'answered' ? 'selected' : ''}>Отвечен</option>
                    <option value="closed" ${item.status === 'closed' ? 'selected' : ''}>Закрыт</option>
                    <option value="open" ${item.status === 'open' ? 'selected' : ''}>Открыт</option>
                </select>
                <div class="inbox-reply-actions">
                    <button type="submit" class="inbox-btn-primary" id="inboxReplyBtn">
                        <i class="fa-solid fa-paper-plane" aria-hidden="true"></i> Сохранить ответ
                    </button>
                </div>
                <div id="inboxReplyResult" class="result" role="status" aria-live="polite"></div>
            </form>
        </article>`;
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

async function submitTicketReply(event, id) {
    event.preventDefault();
    const btn = document.getElementById('inboxReplyBtn');
    const result = document.getElementById('inboxReplyResult');
    const admin_response = document.getElementById('inboxReplyText')?.value || '';
    const status = document.getElementById('inboxReplyStatus')?.value || 'answered';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Сохранение…';
    }
    try {
        await apiCall('POST', `/api/admin/support-tickets/${id}/review`, { status, admin_response });
        if (result) {
            result.className = 'result success';
            result.textContent = 'Ответ сохранён';
        }
        await loadAdminInbox();
    } catch (e) {
        if (result) {
            result.className = 'result error';
            result.textContent = e.message || 'Ошибка';
        }
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-paper-plane" aria-hidden="true"></i> Сохранить ответ';
        }
    }
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
