async function loadInventory() {
    const container = document.getElementById('inventoryContent');
    if (!container) return;
    if (!currentUser?.authenticated) {
        container.innerHTML = '<p class="empty-state">Войдите через Discord</p>';
        return;
    }
    container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const data = await apiCall('GET', '/api/inventory');
        let html = '';

        html += '<div class="inventory-section">';
        html += '<h3><i class="fa-solid fa-heart"></i> Донат-подписка</h3>';
        if (data.sponsor) {
            html += `
                <div class="sponsor-current">
                    <img src="${data.sponsor.icon}" alt="${escapeHtml(data.sponsor.name)}" class="sponsor-icon-large">
                    <div>
                        <div class="sponsor-level-badge">Уровень ${data.sponsor.level}</div>
                        <div class="sponsor-name">${escapeHtml(data.sponsor.name)}</div>
                    </div>
                </div>`;
        } else {
            html += '<p class="inventory-empty">Подписка не активна</p>';
        }
        html += '<div class="sponsor-tiers">';
        (data.tiers || []).forEach(t => {
            html += `
                <div class="sponsor-tier ${t.active ? 'active' : ''}">
                    <img src="${t.icon}" alt="${escapeHtml(t.name)}" class="sponsor-tier-icon">
                    <span class="sponsor-tier-level">${t.level}</span>
                    <span class="sponsor-tier-name">${escapeHtml(t.name)}</span>
                </div>`;
        });
        html += '</div></div>';

        html += '<div class="inventory-section">';
        html += '<h3><i class="fa-solid fa-ticket"></i> Билеты</h3>';
        if (data.tickets?.length) {
            html += '<div class="tickets-grid">';
            data.tickets.forEach(t => {
                html += `
                    <div class="ticket-card">
                        <div class="ticket-name">${escapeHtml(t.name)}</div>
                        <div class="ticket-amount">×${t.amount}</div>
                    </div>`;
            });
            html += '</div>';
        } else {
            html += '<p class="inventory-empty">Нет билетов. Привяжите Discord к игровому аккаунту, чтобы видеть билеты.</p>';
        }
        html += '</div>';

        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    }
}
