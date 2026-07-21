async function initSupportSection() {
    await loadSupportContacts();
    const wrap = document.getElementById('supportMyTicketsWrap');
    if (currentUser?.authenticated) {
        if (wrap) wrap.hidden = false;
        loadMySupportTickets();
        const contact = document.getElementById('supportContact');
        if (contact && !contact.value && currentUser.username) {
            contact.value = currentUser.username;
        }
    } else if (wrap) {
        wrap.hidden = true;
    }
}

async function loadSupportContacts() {
    try {
        const data = await apiCall('GET', '/api/support/contacts');
        const email = data.email || 'support@ministation.ru';
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
        /* keep defaults from HTML */
    }
}

async function submitSupportTicket(event) {
    event.preventDefault();
    const result = document.getElementById('supportFormResult');
    const contact = document.getElementById('supportContact')?.value.trim() || '';
    const subject = document.getElementById('supportSubject')?.value.trim() || '';
    const body = document.getElementById('supportBody')?.value.trim() || '';
    const formData = new FormData();
    formData.append('contact', contact);
    formData.append('subject', subject);
    formData.append('body', body);
    try {
        const res = await apiCall('POST', '/api/support/tickets', formData);
        if (result) {
            result.className = 'result success';
            result.textContent = `Тикет #${res.ticket_id} отправлен. Ответим на указанный контакт.`;
        }
        const form = document.getElementById('supportTicketForm');
        if (form) form.reset();
        if (currentUser?.authenticated) loadMySupportTickets();
    } catch (e) {
        if (result) {
            result.className = 'result error';
            result.textContent = e.message || 'Не удалось отправить';
        }
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
        const statusLabel = { open: 'Открыт', answered: 'Отвечен', closed: 'Закрыт' };
        box.innerHTML = items.map(t => `
            <div class="support-ticket-row">
                <div class="support-ticket-head">
                    <strong>#${t.id} · ${escapeHtml(t.subject || '')}</strong>
                    <span class="support-ticket-status status-${escapeHtml(t.status || 'open')}">${statusLabel[t.status] || t.status}</span>
                </div>
                <p class="support-ticket-body">${escapeHtml(t.body || '')}</p>
                ${t.admin_response ? `<p class="support-ticket-reply"><strong>Ответ:</strong> ${escapeHtml(t.admin_response)}</p>` : ''}
                <div class="support-ticket-meta">${escapeHtml(String(t.created_at || ''))}</div>
            </div>
        `).join('');
    } catch {
        box.innerHTML = '<p class="error">Не удалось загрузить тикеты</p>';
    }
}

async function loadAdminSupportTickets(reset = true) {
    const box = document.getElementById('adminSupportTicketsContent');
    if (!box) return;
    const filter = document.getElementById('adminSupportFilter')?.value || 'open';
    try {
        const q = filter ? `?status=${encodeURIComponent(filter)}` : '';
        const items = await apiCall('GET', `/api/admin/support-tickets${q}`);
        if (!items.length) {
            box.innerHTML = '<p class="empty-state">Тикетов нет</p>';
            return;
        }
        const statusLabel = { open: 'Открыт', answered: 'Отвечен', closed: 'Закрыт' };
        box.innerHTML = items.map(t => `
            <div class="admin-appeal-card support-admin-card">
                <div class="admin-appeal-head">
                    <strong>#${t.id} · ${escapeHtml(t.subject || '')}</strong>
                    <span>${statusLabel[t.status] || t.status}</span>
                </div>
                <div class="admin-hint">Контакт: ${escapeHtml(t.contact || '—')} · игрок: ${escapeHtml(t.player_id || 'гость')}</div>
                <p>${escapeHtml(t.body || '')}</p>
                ${t.admin_response ? `<p><strong>Ответ:</strong> ${escapeHtml(t.admin_response)}</p>` : ''}
                <div class="admin-inline-form">
                    <textarea id="supportReply_${t.id}" rows="2" placeholder="Ответ поддержки...">${escapeHtml(t.admin_response || '')}</textarea>
                    <select id="supportStatus_${t.id}">
                        <option value="answered" ${t.status === 'answered' ? 'selected' : ''}>Отвечен</option>
                        <option value="closed" ${t.status === 'closed' ? 'selected' : ''}>Закрыт</option>
                        <option value="open" ${t.status === 'open' ? 'selected' : ''}>Открыт</option>
                    </select>
                    <button type="button" onclick="reviewSupportTicket(${t.id})">Сохранить</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        box.innerHTML = `<p class="error">${escapeHtml(e.message || 'Ошибка')}</p>`;
    }
}

async function reviewSupportTicket(id) {
    const status = document.getElementById(`supportStatus_${id}`)?.value || 'answered';
    const admin_response = document.getElementById(`supportReply_${id}`)?.value || '';
    try {
        await apiCall('POST', `/api/admin/support-tickets/${id}/review`, { status, admin_response });
        loadAdminSupportTickets(false);
    } catch (e) {
        alert(e.message || 'Ошибка');
    }
}
