async function loadChat() {
    try {
        const res = await fetch(`${API_BASE}/api/chat`);
        const messages = await res.json();
        const container = document.getElementById('chatMessages');
        if (container) {
            container.innerHTML = messages.map(m => `
                <div class="chat-message">
                    ${m.avatar ? `<img src="${m.avatar}" class="chat-avatar" alt="">` : ''}
                    <div class="chat-content">
                        <div class="chat-username">${m.username}</div>
                        <div class="chat-text">${escapeHtml(m.message)}</div>
                        <div class="chat-time">${new Date(m.timestamp).toLocaleTimeString()}</div>
                    </div>
                </div>
            `).join('');
            container.scrollTop = container.scrollHeight;
        }
    } catch (e) {}
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    try {
        await apiCall('POST', '/api/chat', { message });
        input.value = '';
        await loadChat();
    } catch (e) {
        alert(e.message);
    }
}