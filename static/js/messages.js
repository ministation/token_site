let currentPmPartnerId = null;

async function loadDialogs() {
    if (!currentUser?.player) {
        document.getElementById('dialogsList').innerHTML = '<p class="empty-state">Войдите, чтобы видеть сообщения</p>';
        return;
    }
    try {
        const dialogs = await apiCall('GET', '/api/messages/dialogs');
        const container = document.getElementById('dialogsList');
        if (!dialogs.length) {
            container.innerHTML = '<p class="empty-state">Нет диалогов</p>';
            return;
        }
        container.innerHTML = dialogs.map(d => `
            <div class="dialog-item ${currentPmPartnerId === d.other_id ? 'active' : ''}"
                 onclick='openConversation(${JSON.stringify(d.other_id)}, ${JSON.stringify(d.nickname || 'Игрок')})'>
                <div class="dialog-name">${escapeHtml(d.nickname || 'Игрок')}</div>
                <div class="dialog-preview">${escapeHtml(d.last_msg || '')}</div>
                ${d.unread ? `<span class="dialog-unread">${d.unread}</span>` : ''}
            </div>
        `).join('');
    } catch (e) {
        document.getElementById('dialogsList').innerHTML = '<p class="error">Не удалось загрузить диалоги</p>';
    }
}

async function openConversation(partnerId, nickname) {
    currentPmPartnerId = partnerId;
    const title = document.getElementById('conversationTitle');
    if (title) title.textContent = nickname || 'Диалог';
    await loadDialogs();
    await loadConversation(partnerId);
}

async function loadConversation(partnerId) {
    const container = document.getElementById('currentConversation');
    if (!container) return;
    try {
        const messages = await apiCall('GET', `/api/messages/conversation/${partnerId}`);
        if (!messages.length) {
            container.innerHTML = '<p class="empty-state">Начните переписку</p>';
            return;
        }
        const myId = currentUser.player.player_id;
        container.innerHTML = messages.reverse().map(m => {
            const own = m.sender_id === myId;
            return `<div class="pm-message ${own ? 'own' : ''}">
                <div class="pm-bubble">${escapeHtml(m.content)}</div>
                <div class="pm-time">${new Date(m.created_at).toLocaleString()}</div>
            </div>`;
        }).join('');
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        container.innerHTML = '<p class="error">Ошибка загрузки</p>';
    }
}

async function sendPrivateMessage() {
    if (!currentPmPartnerId) {
        alert('Выберите диалог');
        return;
    }
    const input = document.getElementById('pmInput');
    const content = input?.value.trim();
    if (!content) return;
    try {
        await apiCall('POST', '/api/messages/send', {
            receiver_id: currentPmPartnerId,
            content
        });
        input.value = '';
        await loadConversation(currentPmPartnerId);
        await loadDialogs();
    } catch (e) {
        alert(e.message);
    }
}

function startConversationWith(playerId, nickname) {
    showSection('messages');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector('.nav-btn[data-section="messages"]');
    if (btn) btn.classList.add('active');
    openConversation(playerId, nickname);
}
