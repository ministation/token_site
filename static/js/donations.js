let donateCatalog = null;
let selectedDonateTierId = null;
let selectedDonatePackId = null;
let selectedDonateMethod = 2;
let donateActiveTab = 'tiers';
let currentDonateOrderId = null;
let donateStatusPoll = null;

const COIN_IMG = '<img src="/static/coin.png" class="coin-icon-result donate-coin-inline" alt="">';
const DONATE_METHOD_KEY = 'donatePaymentMethod';
const METHOD_ALIASES = { 10: 11, 12: 2 }; // 10→МИР(11), международные убраны

function normalizeDonateMethod(id) {
    let n = Number(id);
    if (!Number.isFinite(n)) n = 2;
    if (METHOD_ALIASES[n] != null) n = METHOD_ALIASES[n];
    return n;
}

function loadSavedDonateMethod(fallback = 2) {
    try {
        const raw = sessionStorage.getItem(DONATE_METHOD_KEY);
        if (raw != null && raw !== '') return normalizeDonateMethod(raw);
    } catch (_) { /* ignore */ }
    return normalizeDonateMethod(fallback);
}

function saveDonateMethod(id) {
    selectedDonateMethod = normalizeDonateMethod(id);
    try {
        sessionStorage.setItem(DONATE_METHOD_KEY, String(selectedDonateMethod));
    } catch (_) { /* ignore */ }
}

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
        const methods = donateCatalog.methods || [];
        const allowed = new Set(methods.map(m => Number(m.id)));
        let method = loadSavedDonateMethod(donateCatalog.default_method || 2);
        if (!allowed.has(method) && methods.length) {
            method = Number(methods[0].id);
        }
        saveDonateMethod(method);
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
            startToolboxAnimations(packsBox);
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
        ? `<li class="donate-perk-coins"><span class="coin-qty">${t.coins}${COIN_IMG}</span><span class="donate-perk-period">в месяц</span></li>`
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
    if (coins >= 40) return 2;
    return 1;
}

function renderPackCoinPile(coins) {
    const n = packPileCount(coins);
    const imgs = Array.from({ length: n }, (_, i) =>
        `<img src="/static/coin.png" alt="" class="donate-pack-coin-art pile-coin pile-coin--${i}" width="56" height="56">`
    ).join('');
    return `<div class="donate-pack-pile donate-pack-pile--${n}" aria-hidden="true">${imgs}</div>`;
}

/** 1 рюкзак, 2 тулбокс, 3 ящик, 4 сейф, 5 суперприпасы. */
function packVisual(p) {
    if (p.id === 1) return { kind: 'img', src: '/static/icons/backpack-coins-self-made.png', size: 'md', alt: 'Рюкзак монет' };
    if (p.id === 2) return { kind: 'toolbox', size: 'md', alt: 'Тулбокс монет' };
    if (p.id === 3) return { kind: 'img', src: '/static/icons/coins-self-made.png', size: 'md', alt: 'Ящик монет' };
    if (p.id === 4) return { kind: 'img', src: '/static/icons/case.png', size: 'md', alt: 'Сейф монет' };
    if (p.id === 5) return { kind: 'img', src: '/static/icons/syndie-coins-self-made.png', size: 'lg', alt: 'Ящик суперприпасов монет' };
    return null;
}

function renderPackVisual(p) {
    const v = packVisual(p);
    if (!v) return renderPackCoinPile(p.coins);
    if (v.kind === 'toolbox') {
        return `<span class="donate-pack-toolbox-wrap donate-pack-crate--${v.size}" aria-hidden="true">
            <span class="donate-pack-toolbox" role="img" aria-label="${escapeHtml(v.alt)}"></span>
        </span>`;
    }
    return `<img src="${v.src}" alt="${escapeHtml(v.alt)}" class="donate-pack-crate donate-pack-crate--${v.size}" width="32" height="32">`;
}

function startToolboxAnimations(root) {
    const nodes = (root || document).querySelectorAll('.donate-pack-toolbox');
    nodes.forEach(el => {
        if (el.dataset.animating === '1') return;
        el.dataset.animating = '1';
        const cols = 5;
        const total = 18;
        const fw = 32;
        const fh = 32;
        let frame = 0;
        const tick = () => {
            if (!el.isConnected) return;
            const col = frame % cols;
            const row = Math.floor(frame / cols);
            el.style.backgroundPosition = `-${col * fw}px -${row * fh}px`;
            frame = (frame + 1) % total;
            el._toolboxTimer = setTimeout(tick, 110);
        };
        tick();
    });
}

function renderDonatePackCard(p) {
    const active = selectedDonatePackId === p.id ? ' active' : '';
    const featured = p.featured ? ' featured' : '';
    const badge = p.badge ? `<span class="donate-tier-badge">${escapeHtml(p.badge)}</span>` : '';
    const visualMeta = packVisual(p);
    return `
        <article class="donate-pack-card${active}${featured}" data-pack="${p.id}">
            ${badge}
            <button type="button" class="donate-pack-select" onclick="selectDonatePack(${p.id})" aria-pressed="${active ? 'true' : 'false'}">
                <div class="donate-pack-visual${visualMeta ? ' has-crate' : ''}">
                    ${renderPackVisual(p)}
                </div>
                <div class="donate-pack-body">
                    <div class="donate-pack-name">${escapeHtml(p.name)}</div>
                    <div class="donate-pack-amount">
                        <span class="donate-pack-coins coin-qty">${p.coins}<img src="/static/coin.png" class="coin-icon-result donate-coin-inline" alt=""></span>
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
    saveDonateMethod(input.value);
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
    const hint = document.getElementById('donateHint');
    const icon = document.getElementById('donateSelectedIcon');
    const name = document.getElementById('donateSelectedName');
    const price = document.getElementById('donateSelectedPrice');

    const tier = (donateCatalog?.tiers || []).find(t => t.id === selectedDonateTierId);
    const pack = (donateCatalog?.coin_packs || []).find(p => p.id === selectedDonatePackId);
    const item = tier || pack;
    const mode = donateCatalog?.mode || '';

    if (hint && mode === 'platega') {
        hint.innerHTML = 'Оплачивая заказ, вы принимаете <a href="/#/offer">публичную оферту</a>. '
            + 'Откроется безопасная страница Platega (СБП / карта). После оплаты привилегии активируются автоматически.';
    } else if (hint && mode === 'robokassa') {
        hint.innerHTML = 'Оплачивая заказ, вы принимаете <a href="/#/offer">публичную оферту</a>. '
            + 'Откроется безопасная страница Robokassa (СБП / карта). После оплаты привилегии активируются автоматически.';
    }

    if (!item) {
        if (empty) empty.hidden = false;
        if (selected) selected.hidden = true;
        if (methods) methods.hidden = true;
        if (contactWrap) contactWrap.hidden = true;
        if (payBtn) payBtn.disabled = true;
        if (icon) {
            icon.hidden = false;
            icon.removeAttribute('src');
            icon.alt = '';
        }
        const toolboxEl = document.getElementById('donateSelectedToolbox');
        if (toolboxEl) toolboxEl.hidden = true;
        return;
    }

    if (empty) empty.hidden = true;
    if (selected) selected.hidden = false;
    // При Robokassa способ выбирается на их стороне — показываем иконки как подсказку
    if (methods) methods.hidden = false;
    if (contactWrap) contactWrap.hidden = false;
    if (payBtn) payBtn.disabled = false;

    if (tier) {
        const toolboxEl = document.getElementById('donateSelectedToolbox');
        if (toolboxEl) toolboxEl.hidden = true;
        if (icon) {
            icon.hidden = false;
            icon.src = tier.icon;
            icon.alt = tier.name;
        }
        if (name) name.textContent = tier.name;
        if (price) price.textContent = `${tier.price_label} / мес`;
    } else if (pack) {
        if (icon) {
            const visual = packVisual(pack);
            let toolboxEl = document.getElementById('donateSelectedToolbox');
            if (visual?.kind === 'toolbox') {
                icon.hidden = true;
                if (!toolboxEl) {
                    toolboxEl = document.createElement('span');
                    toolboxEl.id = 'donateSelectedToolbox';
                    toolboxEl.className = 'donate-selected-icon donate-pack-toolbox';
                    toolboxEl.setAttribute('role', 'img');
                    icon.insertAdjacentElement('afterend', toolboxEl);
                }
                toolboxEl.hidden = false;
                toolboxEl.setAttribute('aria-label', visual.alt);
                startToolboxAnimations(toolboxEl.parentElement);
            } else {
                if (toolboxEl) toolboxEl.hidden = true;
                icon.hidden = false;
                icon.src = visual ? visual.src : '/static/coin.png';
                icon.alt = visual ? visual.alt : 'Монетки';
            }
        }
        if (name) name.textContent = pack.name;
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
    if (isTier && !currentUser?.authenticated) {
        if (result) {
            result.className = 'result error';
            result.textContent = 'Для покупки подписки войдите через Discord';
        }
        return;
    }

    const formData = new FormData();
    formData.append('product_type', isCoins ? 'coins' : 'tier');
    formData.append('tier_id', String(selectedDonateTierId || 0));
    formData.append('pack_id', String(selectedDonatePackId || 0));
    formData.append('payment_method', String(normalizeDonateMethod(selectedDonateMethod || 2)));
    formData.append('contact', document.getElementById('donateContact')?.value.trim() || '');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Создание заказа…';
    }
    try {
        const data = await apiCall('POST', '/api/donations/checkout', formData);
        if (data.redirect || data.pay_path) {
            if (result) {
                result.className = 'result success';
                result.textContent = 'Перенаправляем на оплату…';
            }
            window.location.href = data.pay_path || data.redirect;
            return;
        }
        if (data.mode === 'manual_sbp' || data.sbp) {
            showDonateWaitPanel(data);
            return;
        }
        if (data.transaction_id) {
            showDonateWaitPanel(data);
            return;
        }
        throw new Error('Не удалось открыть оплату');
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

function showDonateWaitPanel(data) {
    currentDonateOrderId = data.transaction_id;
    const wait = document.getElementById('donateWaitPanel');
    const shop = document.getElementById('donateShopMain');
    if (!wait) {
        // Старый HTML без панели ожидания — перезагрузка на wait URL
        if (data.transaction_id) {
            window.location.href = `/donate?order=${encodeURIComponent(data.transaction_id)}&wait=1`;
        }
        return;
    }
    if (shop) shop.hidden = true;
    wait.hidden = false;

    const sbp = data.sbp || donateCatalog?.sbp || {};
    const item = data.item || {};
    const qr = document.getElementById('donateWaitQr');
    if (qr) qr.src = sbp.qr || '/static/payment/sbp-qr.png';
    const link = document.getElementById('donateWaitLink');
    if (link) {
        link.href = sbp.link || (donateCatalog?.sbp?.link) || '#';
    }
    const txEl = document.getElementById('donateWaitTx');
    if (txEl) txEl.textContent = (data.transaction_id || '').slice(0, 8) + '…';
    const amountEl = document.getElementById('donateWaitAmount');
    if (amountEl) amountEl.textContent = data.amount_label || `${data.amount_rub || ''} ₽`;
    const itemEl = document.getElementById('donateWaitItem');
    if (itemEl) itemEl.textContent = item.name || data.tier_name || 'Заказ';
    const statusEl = document.getElementById('donateWaitStatus');
    if (statusEl) statusEl.textContent = statusLabel(data.status || 'pending');
    const markBtn = document.getElementById('donateMarkPaidBtn');
    if (markBtn) {
        markBtn.disabled = (data.status === 'awaiting_confirmation' || data.status === 'confirmed');
        markBtn.innerHTML = (data.status === 'awaiting_confirmation' || data.status === 'confirmed')
            ? '<i class="fa-solid fa-hourglass-half"></i> Ожидание платежа'
            : '<i class="fa-solid fa-check"></i> Я оплатил';
    }
    const res = document.getElementById('donateWaitResult');
    if (res) { res.className = 'result'; res.textContent = ''; }
    history.replaceState({}, '', `/donate?order=${encodeURIComponent(data.transaction_id)}&wait=1`);
    startDonateStatusPoll();
}

function hideDonateWaitPanel() {
    stopDonateStatusPoll();
    currentDonateOrderId = null;
    const wait = document.getElementById('donateWaitPanel');
    const shop = document.getElementById('donateShopMain');
    if (wait) wait.hidden = true;
    if (shop) shop.hidden = false;
    history.replaceState({}, '', '/donate');
}

function statusLabel(st) {
    const map = {
        pending: 'ожидание платежа',
        awaiting_confirmation: 'ожидание платежа',
        confirmed: 'оплата получена',
        canceled: 'отменён',
        failed: 'ошибка',
    };
    return map[st] || 'ожидание платежа';
}

async function markDonationPaid() {
    if (!currentDonateOrderId) return;
    const btn = document.getElementById('donateMarkPaidBtn');
    const res = document.getElementById('donateWaitResult');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Отправка…';
    }
    try {
        const data = await apiCall('POST', `/api/donations/mark-paid/${encodeURIComponent(currentDonateOrderId)}`);
        if (res) {
            res.className = 'result success';
            res.textContent = 'Платёж принят в обработку. Ожидайте зачисления.';
        }
        const statusEl = document.getElementById('donateWaitStatus');
        if (statusEl) statusEl.textContent = statusLabel('awaiting_confirmation');
        if (btn) btn.innerHTML = '<i class="fa-solid fa-hourglass-half"></i> Ожидание платежа';
        startDonateStatusPoll();
    } catch (e) {
        if (res) {
            res.className = 'result error';
            res.textContent = e.message || 'Не удалось отправить статус';
        }
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Я оплатил';
        }
    }
}

function startDonateStatusPoll() {
    stopDonateStatusPoll();
    if (!currentDonateOrderId) return;
    donateStatusPoll = setInterval(refreshDonateOrderStatus, 8000);
    refreshDonateOrderStatus();
}

function stopDonateStatusPoll() {
    if (donateStatusPoll) {
        clearInterval(donateStatusPoll);
        donateStatusPoll = null;
    }
}

async function refreshDonateOrderStatus() {
    if (!currentDonateOrderId) return;
    try {
        const data = await apiCall('GET', `/api/donations/status/${encodeURIComponent(currentDonateOrderId)}`);
        const statusEl = document.getElementById('donateWaitStatus');
        if (statusEl) statusEl.textContent = statusLabel(data.status || '');
        const markBtn = document.getElementById('donateMarkPaidBtn');
        if (markBtn && (data.status === 'awaiting_confirmation' || data.status === 'confirmed')) {
            markBtn.disabled = true;
            markBtn.innerHTML = data.status === 'confirmed'
                ? '<i class="fa-solid fa-check-double"></i> Оплата получена'
                : '<i class="fa-solid fa-hourglass-half"></i> Ожидание платежа';
        }
        if (data.status === 'confirmed') {
            stopDonateStatusPoll();
            const banner = document.getElementById('donatePayStatus');
            if (banner) {
                banner.hidden = false;
                banner.className = 'donate-pay-banner ok';
                if ((data.product_type || '') === 'coins') {
                    banner.textContent = data.fulfilled
                        ? `Оплата получена: ${data.coins_amount || ''} монет зачислено.`
                        : `Оплата получена (${data.amount_rub || ''} ₽). Монеты зачислятся автоматически.`;
                } else {
                    banner.textContent = `Оплата получена: ${data.tier_name || 'подписка'} активирована.`;
                }
            }
            const res = document.getElementById('donateWaitResult');
            if (res) {
                res.className = 'result success';
                res.textContent = 'Готово! Привилегии выданы.';
            }
        }
    } catch (_) { /* ignore poll errors */ }
}

async function handleDonateReturnQuery() {
    const params = new URLSearchParams(window.location.search || '');
    let order = params.get('order');
    let result = params.get('result');
    let wait = params.get('wait');
    let paid = params.get('paid');
    if (!order && location.hash.includes('?')) {
        const hq = new URLSearchParams(location.hash.split('?')[1] || '');
        order = hq.get('order');
        result = hq.get('result');
        wait = hq.get('wait');
        paid = hq.get('paid');
    }

    if (paid === '1' || paid === '0') {
        const banner = document.getElementById('donatePayStatus');
        if (banner && !order) {
            banner.hidden = false;
            if (paid === '1') {
                banner.className = 'donate-pay-banner ok';
                banner.textContent = 'Оплата прошла. Если привилегии не появились сразу — обновите страницу через минуту.';
            } else {
                banner.className = 'donate-pay-banner fail';
                banner.textContent = 'Оплата не завершена. Попробуйте снова.';
            }
        }
    }

    if (!order) return;

    if (wait === '1' && !result && paid !== '1') {
        try {
            const data = await apiCall('GET', `/api/donations/order/${encodeURIComponent(order)}`);
            showDonateWaitPanel(data);
            return;
        } catch (_) { /* fall through */ }
    }

    const banner = document.getElementById('donatePayStatus');
    if (!banner) return;
    banner.hidden = false;
    banner.className = 'donate-pay-banner';
    banner.textContent = 'Проверяем статус оплаты…';
    try {
        const data = await apiCall('GET', `/api/donations/status/${encodeURIComponent(order)}`);
        const st = data.status || '';
        if (st === 'confirmed' || result === 'success' || paid === '1') {
            banner.classList.add('ok');
            if ((data.product_type || '') === 'coins') {
                banner.textContent = data.fulfilled
                    ? `Оплата получена: ${data.coins_amount || ''} монет зачислено.`
                    : `Оплата получена (${data.amount_rub || ''} ₽).`;
            } else {
                banner.textContent = `Оплата получена: ${data.tier_name || 'тариф'} (${data.amount_rub || ''} ₽).`;
            }
            if (st !== 'confirmed') {
                // Result URL мог ещё не успеть — опрашиваем
                currentDonateOrderId = order;
                startDonateStatusPoll();
            }
        } else if (st === 'awaiting_confirmation') {
            showDonateWaitPanel(data);
            banner.hidden = true;
        } else if (st === 'canceled' || result === 'fail' || paid === '0') {
            banner.classList.add('fail');
            banner.textContent = 'Оплата не завершена. Попробуйте снова.';
        } else {
            currentDonateOrderId = order;
            startDonateStatusPoll();
            banner.textContent = 'Ожидаем подтверждение оплаты…';
        }
    } catch {
        banner.classList.add('fail');
        banner.textContent = 'Не удалось проверить статус заказа.';
    }
}
