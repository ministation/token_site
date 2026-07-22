let donateCatalog = null;
let selectedDonateTierId = null;
let selectedDonatePackId = null;
let selectedDonateMethod = 2;
let donateActiveTab = 'tiers';

const COIN_IMG = '<img src="/static/coin.png" class="coin-icon-result donate-coin-inline" alt="">';

async function initDonateSection() {
    selectedDonateTierId = null;
    selectedDonatePackId = null;
    donateActiveTab = 'tiers';
    await loadDonateCatalog();
    handleDonateReturnQuery();
}

function switchDonateTab(tab) {
    donateActiveTab = tab === 'coins' ? 'coins' : 'tiers';
    document.querySelectorAll('.donate-tab').forEach(btn => {
        const on = btn.dataset.tab === donateActiveTab;
        btn.classList.toggle('active', on);
        btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    const tiers = document.getElementById('donateTiers');
    const packs = document.getElementById('donateCoinPacks');
    if (tiers) tiers.hidden = donateActiveTab !== 'tiers';
    if (packs) packs.hidden = donateActiveTab !== 'coins';
    selectedDonateTierId = null;
    selectedDonatePackId = null;
    document.querySelectorAll('.donate-tier-card, .donate-pack-card').forEach(el => {
        el.classList.remove('active');
        const btn = el.querySelector('button');
        if (btn) btn.setAttribute('aria-pressed', 'false');
    });
    updateDonateCheckoutUI();
}

async function loadDonateCatalog() {
    const box = document.getElementById('donateTiers');
    const packsBox = document.getElementById('donateCoinPacks');
    if (!box && !packsBox) return;
    try {
        donateCatalog = await apiCall('GET', '/api/donations/catalog');
        selectedDonateMethod = donateCatalog.default_method || 2;
        const tiers = donateCatalog.tiers || [];
        const packs = donateCatalog.coin_packs || [];
        if (box) {
            box.innerHTML = tiers.length
                ? tiers.map(t => renderDonateTierCard(t)).join('')
                : '<p class="empty-state">Тарифы недоступны</p>';
        }
        if (packsBox) {
            packsBox.innerHTML = packs.length
                ? packs.map(p => renderDonatePackCard(p)).join('')
                : '<p class="empty-state">Пакеты недоступны</p>';
        }
        renderDonateMethods();
        switchDonateTab(donateActiveTab);
        updateDonateCheckoutUI();
    } catch (e) {
        if (box) box.innerHTML = `<p class="error">${escapeHtml(e.message || 'Ошибка загрузки')}</p>`;
    }
}

function renderDonateTierCard(t) {
    const coinLine = t.coins
        ? `<li class="donate-perk-coins"><span>${t.coins}</span> ${COIN_IMG} <span class="donate-perk-period">в месяц</span></li>`
        : '';
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
                    <ul class="donate-tier-perks">${coinLine}${perks}</ul>
                </div>
            </button>
        </article>`;
}

function packPileCount(coins) {
    if (coins >= 250) return 5;
    if (coins >= 150) return 4;
    if (coins >= 80) return 3;
    if (coins >= 40) return 2;
    return 1;
}

function renderPackCoinPile(coins) {
    const n = packPileCount(coins);
    const imgs = Array.from({ length: n }, (_, i) =>
        `<img src="/static/coin.png" alt="" class="donate-pack-coin-art pile-coin pile-coin--${i}" width="72" height="72">`
    ).join('');
    return `<div class="donate-pack-pile donate-pack-pile--${n}" aria-hidden="true">${imgs}</div>`;
}

function renderDonatePackCard(p) {
    const active = selectedDonatePackId === p.id ? ' active' : '';
    const featured = p.featured ? ' featured' : '';
    const badge = p.badge ? `<span class="donate-tier-badge">${escapeHtml(p.badge)}</span>` : '';
    return `
        <article class="donate-pack-card${active}${featured}" data-pack="${p.id}">
            ${badge}
            <button type="button" class="donate-pack-select" onclick="selectDonatePack(${p.id})" aria-pressed="${active ? 'true' : 'false'}">
                <div class="donate-pack-visual">
                    ${renderPackCoinPile(p.coins)}
                </div>
                <div class="donate-pack-body">
                    <div class="donate-pack-name">${escapeHtml(p.name)}</div>
                    <div class="donate-pack-amount">
                        <span class="donate-pack-coins">${p.coins}</span>
                        <img src="/static/coin.png" class="coin-icon-result donate-coin-inline" alt="">
                    </div>
                    <div class="donate-pack-price">${escapeHtml(p.price_label)}</div>
                </div>
            </button>
        </article>`;
}

function renderDonateMethods() {
    const list = document.getElementById('donateMethodList');
    if (!list || !donateCatalog) return;
    const methods = donateCatalog.methods || [];
    list.innerHTML = methods.map(m => `
        <label class="donate-method-option${Number(m.id) === Number(selectedDonateMethod) ? ' is-active' : ''}">
            <input type="radio" name="donateMethod" value="${m.id}"
                ${Number(m.id) === Number(selectedDonateMethod) ? 'checked' : ''}
                onchange="onDonateMethodChange(this)">
            <span class="donate-method-icon-wrap">
                <img class="donate-method-icon" src="${escapeHtml(m.icon || '')}" alt="${escapeHtml(m.label || '')}"
                    loading="lazy">
            </span>
            <span class="donate-method-text">
                <strong>${escapeHtml(m.label)}</strong>
                <small>${escapeHtml(m.hint || '')}</small>
            </span>
        </label>
    `).join('');
}

function onDonateMethodChange(input) {
    selectedDonateMethod = Number(input.value);
    document.querySelectorAll('.donate-method-option').forEach(el => {
        el.classList.toggle('is-active', !!el.querySelector('input')?.checked);
    });
}

function selectDonateTier(tierId) {
    donateActiveTab = 'tiers';
    selectedDonateTierId = Number(tierId);
    selectedDonatePackId = null;
    document.querySelectorAll('.donate-tier-card').forEach(el => {
        const on = Number(el.dataset.tier) === selectedDonateTierId;
        el.classList.toggle('active', on);
        const btn = el.querySelector('.donate-tier-select');
        if (btn) btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    document.querySelectorAll('.donate-pack-card').forEach(el => {
        el.classList.remove('active');
        const btn = el.querySelector('.donate-pack-select');
        if (btn) btn.setAttribute('aria-pressed', 'false');
    });
    updateDonateCheckoutUI();
}

function selectDonatePack(packId) {
    donateActiveTab = 'coins';
    selectedDonatePackId = Number(packId);
    selectedDonateTierId = null;
    document.querySelectorAll('.donate-pack-card').forEach(el => {
        const on = Number(el.dataset.pack) === selectedDonatePackId;
        el.classList.toggle('active', on);
        const btn = el.querySelector('.donate-pack-select');
        if (btn) btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    document.querySelectorAll('.donate-tier-card').forEach(el => {
        el.classList.remove('active');
        const btn = el.querySelector('.donate-tier-select');
        if (btn) btn.setAttribute('aria-pressed', 'false');
    });
    updateDonateCheckoutUI();
}

function updateDonateCheckoutUI() {
    const empty = document.getElementById('donateSelectedEmpty');
    const selected = document.getElementById('donateSelected');
    const methods = document.getElementById('donateMethods');
    const contactWrap = document.getElementById('donateContactWrap');
    const payBtn = document.getElementById('donatePayBtn');
    const icon = document.getElementById('donateSelectedIcon');
    const name = document.getElementById('donateSelectedName');
    const price = document.getElementById('donateSelectedPrice');

    const tier = (donateCatalog?.tiers || []).find(t => t.id === selectedDonateTierId);
    const pack = (donateCatalog?.coin_packs || []).find(p => p.id === selectedDonatePackId);
    const item = tier || pack;

    if (!item) {
        if (empty) empty.hidden = false;
        if (selected) selected.hidden = true;
        if (methods) methods.hidden = true;
        if (contactWrap) contactWrap.hidden = true;
        if (payBtn) payBtn.disabled = true;
        if (icon) {
            icon.removeAttribute('src');
            icon.alt = '';
        }
        return;
    }

    if (empty) empty.hidden = true;
    if (selected) selected.hidden = false;
    if (methods) methods.hidden = false;
    if (contactWrap) contactWrap.hidden = false;
    if (payBtn) payBtn.disabled = false;

    if (tier) {
        if (icon) {
            icon.hidden = false;
            icon.src = tier.icon;
            icon.alt = tier.name;
        }
        if (name) name.textContent = tier.name;
        if (price) price.textContent = `${tier.price_label} / мес`;
    } else if (pack) {
        if (icon) {
            icon.hidden = false;
            icon.src = '/static/coin.png';
            icon.alt = 'Монетки';
        }
        if (name) name.textContent = `${pack.name}: ${pack.coins}`;
        if (price) price.textContent = pack.price_label;
    }

    const contact = document.getElementById('donateContact');
    if (contact && !contact.value && currentUser?.username) contact.value = currentUser.username;

    if (window.matchMedia('(max-width: 900px)').matches) {
        document.getElementById('donateCheckout')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

async function startDonationCheckout() {
    const result = document.getElementById('donateCheckoutResult');
    const btn = document.getElementById('donatePayBtn');
    const isCoins = !!selectedDonatePackId;
    const isTier = !!selectedDonateTierId;
    if (!isCoins && !isTier) {
        if (result) {
            result.className = 'result error';
            result.textContent = 'Выберите товар';
        }
        return;
    }
    if (donateCatalog && !donateCatalog.configured) {
        if (result) {
            result.className = 'result error';
            result.textContent = 'Оплата сейчас недоступна. Напишите в обращения.';
        }
        return;
    }
    if (isCoins && !currentUser?.authenticated) {
        if (result) {
            result.className = 'result error';
            result.textContent = 'Для покупки монет войдите через Discord';
        }
        return;
    }

    const formData = new FormData();
    formData.append('product_type', isCoins ? 'coins' : 'tier');
    formData.append('tier_id', String(selectedDonateTierId || 0));
    formData.append('pack_id', String(selectedDonatePackId || 0));
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
            btn.disabled = !(selectedDonateTierId || selectedDonatePackId);
            btn.innerHTML = '<i class="fa-solid fa-credit-card"></i> Купить';
        }
    }
}

async function handleDonateReturnQuery() {
    const params = new URLSearchParams(window.location.search || '');
    let order = params.get('order');
    let result = params.get('result');
    if (!order && location.hash.includes('?')) {
        const hq = new URLSearchParams(location.hash.split('?')[1] || '');
        order = hq.get('order');
        result = hq.get('result');
    }
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
            if ((data.product_type || '') === 'coins') {
                banner.textContent = data.fulfilled
                    ? `Оплата получена: ${data.coins_amount || ''} монет зачислено.`
                    : `Оплата получена (${data.amount_rub || ''} ₽). Монеты зачислятся чуть позже.`;
            } else {
                banner.textContent = `Оплата получена: ${data.tier_name || 'тариф'} (${data.amount_rub || ''} ₽). Привилегии выдаст администрация.`;
            }
        } else if (st === 'canceled' || result === 'fail') {
            banner.classList.add('fail');
            banner.textContent = 'Оплата не завершена. Попробуйте снова.';
        } else {
            banner.textContent = 'Платёж в обработке. Обновите страницу через минуту.';
        }
    } catch {
        banner.classList.add('fail');
        banner.textContent = result === 'success'
            ? 'Оплата принята. Если привилегии не появились, напишите в поддержку.'
            : 'Не удалось проверить статус заказа.';
    }
}
