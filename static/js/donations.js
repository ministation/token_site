let donateCatalog = null;
let selectedDonateTierId = null;
let selectedDonateMethod = 2;

async function initDonateSection() {
    selectedDonateTierId = null;
    await loadDonateCatalog();
    handleDonateReturnQuery();
}

async function loadDonateCatalog() {
    const box = document.getElementById('donateTiers');
    if (!box) return;
    try {
        donateCatalog = await apiCall('GET', '/api/donations/catalog');
        const tiers = donateCatalog.tiers || [];
        selectedDonateMethod = donateCatalog.default_method || 2;
        if (!tiers.length) {
            box.innerHTML = '<p class="empty-state">Тарифы недоступны</p>';
            return;
        }
        box.innerHTML = tiers.map(t => renderDonateTierCard(t)).join('');
        renderDonateMethods();
        const hint = document.getElementById('donateHint');
        if (hint && !donateCatalog.configured) {
            hint.textContent = 'Ключи Platega ещё не заданы на сервере (PLATEGA_MERCHANT_ID / PLATEGA_SECRET). Интерфейс готов — после выдачи ключей оплата заработает.';
        }
        if (selectedDonateTierId) selectDonateTier(selectedDonateTierId);
        else selectDonateTier(null);
    } catch (e) {
        box.innerHTML = `<p class="error">${escapeHtml(e.message || 'Ошибка загрузки')}</p>`;
    }
}

function renderDonateTierCard(t) {
    const perks = (t.perks || []).map(p => `<li><span>${escapeHtml(p)}</span></li>`).join('');
    const active = selectedDonateTierId === t.id ? ' active' : '';
    const featured = t.featured ? ' featured' : '';
    return `
        <article class="donate-tier-card${active}${featured}" data-tier="${t.id}">
            ${t.featured ? '<span class="donate-tier-badge">Популярный</span>' : ''}
            <button type="button" class="donate-tier-select" onclick="selectDonateTier(${t.id})" aria-pressed="${active ? 'true' : 'false'}">
                <div class="donate-tier-media">
                    <img src="${escapeHtml(t.icon)}" alt="" class="donate-tier-icon" width="140" height="140"
                        onerror="this.style.visibility='hidden'">
                </div>
                <div class="donate-tier-copy">
                    <div class="donate-tier-top">
                        <span class="donate-tier-level">Ур. ${t.id}</span>
                        <h3>${escapeHtml(t.name)}</h3>
                    </div>
                    <div class="donate-tier-price">${escapeHtml(t.price_label)} <span>/ мес</span></div>
                    <ul class="donate-tier-perks">${perks}</ul>
                </div>
            </button>
        </article>`;
}

function renderDonateMethods() {
    const list = document.getElementById('donateMethodList');
    if (!list || !donateCatalog) return;
    const methods = donateCatalog.methods || [];
    list.innerHTML = methods.map(m => `
        <label class="donate-method-option">
            <input type="radio" name="donateMethod" value="${m.id}"
                ${Number(m.id) === Number(selectedDonateMethod) ? 'checked' : ''}
                onchange="selectedDonateMethod = Number(this.value)">
            <img class="donate-method-icon" src="${escapeHtml(m.icon || '')}" alt="" width="40" height="28"
                onerror="this.style.display='none'">
            <span class="donate-method-text">
                <strong>${escapeHtml(m.label)}</strong>
                <small>${escapeHtml(m.hint || '')}</small>
            </span>
        </label>
    `).join('');
}

function selectDonateTier(tierId) {
    selectedDonateTierId = tierId == null || tierId === '' ? null : Number(tierId);
    document.querySelectorAll('.donate-tier-card').forEach(el => {
        const on = selectedDonateTierId != null && Number(el.dataset.tier) === selectedDonateTierId;
        el.classList.toggle('active', on);
        const btn = el.querySelector('.donate-tier-select');
        if (btn) btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    const tier = (donateCatalog?.tiers || []).find(t => t.id === selectedDonateTierId);
    const empty = document.getElementById('donateSelectedEmpty');
    const selected = document.getElementById('donateSelected');
    const methods = document.getElementById('donateMethods');
    const contactWrap = document.getElementById('donateContactWrap');
    const payBtn = document.getElementById('donatePayBtn');
    if (!tier) {
        if (empty) empty.hidden = false;
        if (selected) selected.hidden = true;
        if (methods) methods.hidden = true;
        if (contactWrap) contactWrap.hidden = true;
        if (payBtn) payBtn.disabled = true;
        return;
    }
    if (empty) empty.hidden = true;
    if (selected) selected.hidden = false;
    const icon = document.getElementById('donateSelectedIcon');
    const name = document.getElementById('donateSelectedName');
    const price = document.getElementById('donateSelectedPrice');
    if (icon) icon.src = tier.icon;
    if (name) name.textContent = tier.name;
    if (price) price.textContent = `${tier.price_label} / мес`;
    if (methods) methods.hidden = false;
    if (contactWrap) contactWrap.hidden = false;
    const contact = document.getElementById('donateContact');
    if (contact && !contact.value && currentUser?.username) contact.value = currentUser.username;
    if (payBtn) payBtn.disabled = false;

    if (window.matchMedia('(max-width: 900px)').matches) {
        document.getElementById('donateCheckout')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

async function startDonationCheckout() {
    const result = document.getElementById('donateCheckoutResult');
    const btn = document.getElementById('donatePayBtn');
    if (!selectedDonateTierId) {
        if (result) {
            result.className = 'result error';
            result.textContent = 'Выберите тариф';
        }
        return;
    }
    if (donateCatalog && !donateCatalog.configured) {
        if (result) {
            result.className = 'result error';
            result.textContent = 'Platega ещё не подключена: добавьте ключи в .env';
        }
        return;
    }
    const formData = new FormData();
    formData.append('tier_id', String(selectedDonateTierId));
    formData.append('payment_method', String(selectedDonateMethod || 2));
    formData.append('contact', document.getElementById('donateContact')?.value.trim() || '');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Создание платежа…';
    }
    try {
        const data = await apiCall('POST', '/api/donations/checkout', formData);
        if (result) {
            result.className = 'result success';
            result.textContent = 'Перенаправляем на оплату…';
        }
        if (data.redirect) {
            window.location.href = data.redirect;
            return;
        }
        throw new Error('Платёжный шлюз не вернул ссылку');
    } catch (e) {
        if (result) {
            result.className = 'result error';
            result.textContent = e.message || 'Не удалось создать платёж';
        }
    } finally {
        if (btn) {
            btn.disabled = !selectedDonateTierId;
            btn.innerHTML = '<i class="fa-solid fa-credit-card"></i> Перейти к оплате';
        }
    }
}

async function handleDonateReturnQuery() {
    const hash = location.hash || '';
    const q = hash.includes('?') ? hash.split('?')[1] : '';
    if (!q) return;
    const params = new URLSearchParams(q);
    const order = params.get('order');
    const result = params.get('result');
    const banner = document.getElementById('donatePayStatus');
    if (!banner || !order) return;
    banner.hidden = false;
    banner.className = 'donate-pay-banner';
    banner.textContent = 'Проверяем статус оплаты…';
    try {
        const data = await apiCall('GET', `/api/donations/status/${encodeURIComponent(order)}`);
        const st = data.status || '';
        if (st === 'confirmed' || result === 'success') {
            banner.classList.add('ok');
            banner.textContent = `Оплата получена: ${data.tier_name || 'тариф'} · ${data.amount_rub || ''} ₽. Спасибо! Привилегии выдаст администрация.`;
        } else if (st === 'canceled' || result === 'fail') {
            banner.classList.add('fail');
            banner.textContent = 'Оплата не завершена. Можно выбрать тариф и попробовать снова.';
        } else {
            banner.textContent = `Платёж в обработке (${st || 'pending'}). Обновите страницу через минуту.`;
        }
    } catch {
        banner.classList.add('fail');
        banner.textContent = result === 'success'
            ? 'Вернулись после оплаты — статус уточняется. Напишите в поддержку, если привилегии не появились.'
            : 'Не удалось проверить статус заказа.';
    }
}
