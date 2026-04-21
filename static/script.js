const API_BASE = '';
const COIN_ICON = '<img src="/static/coin.png" class="coin-icon-result" alt="">';
let currentUser = null;
let slotInterval = null;
let currentProfileId = null; // Для просмотра профиля

const SLOT_SYMBOLS = ['cherry', 'lemon', 'orange', 'grapes', 'diamond', 'seven'];

document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    setupNavigation();
    setupAutocomplete();
    loadTop();
    loadStats();
    if (currentUser?.authenticated) {
        if (currentUser.player) {
            loadMyBalance();
            loadMyDeposits();
            loadMyLoans();
            loadFeed();
        }
        loadChat();
        setInterval(loadChat, 5000);
    }
});

// Навигация
function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const section = btn.dataset.section;
            showSection(section);
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            if (section === 'profile') {
                if (currentUser?.player) {
                    loadMyProfile();
                } else {
                    alert('Привяжите Discord к игровому аккаунту');
                }
            } else if (section === 'home') {
                loadFeed();
            } else if (section === 'search') {
                // Очищаем поле
                document.getElementById('socialSearchInput').value = '';
                document.getElementById('searchResults').innerHTML = '';
            }
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(sectionId + 'Section').classList.add('active');
}

// Аутентификация
async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE}/api/me`);
        const data = await res.json();
        currentUser = data;
        
        if (data.authenticated) {
            document.getElementById('loginBtn').style.display = 'none';
            const panel = document.getElementById('userPanel');
            panel.style.display = 'flex';
            panel.innerHTML = `
                ${data.avatar ? `<img src="${data.avatar}" alt="">` : ''}
                <span id="userName">${data.username}</span>
                <button onclick="logout()">Выйти</button>
            `;
            
            if (data.player) {
                // Показываем разделы, требующие привязки
                document.querySelectorAll('.requires-player').forEach(el => el.style.display = 'block');
            }
        } else {
            document.getElementById('loginBtn').style.display = 'block';
            document.getElementById('userPanel').style.display = 'none';
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }
}

function login() { window.location.href = `${API_BASE}/login`; }
function logout() { window.location.href = `${API_BASE}/logout`; }

// Автодополнение
async function setupAutocomplete() {
    const inputs = ['balanceNick', 'receiverNick'];
    let searchTimeout;
    inputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('input', async (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(async () => {
                    if (e.target.value.length < 2) return;
                    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(e.target.value)}`);
                    const players = await res.json();
                    document.getElementById('playersList').innerHTML = players.map(p => `<option value="${p}">`).join('');
                }, 300);
            });
        }
    });
}

async function apiCall(method, url, body = null) {
    const options = { method, headers: {} };
    if (body) {
        if (body instanceof FormData) {
            options.body = body;
        } else {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
    }
    const res = await fetch(`${API_BASE}${url}`, options);
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Ошибка запроса');
    }
    return await res.json();
}

// ---------- Монетки ----------
async function loadMyBalance() {
    try {
        const data = await apiCall('GET', '/api/balance');
        document.getElementById('myBalance').innerHTML = `<p>Баланс: <strong>${data.balance}</strong> ${COIN_ICON}</p>`;
    } catch (e) {}
}

async function checkBalance() {
    const nick = document.getElementById('balanceNick').value;
    const resultDiv = document.getElementById('balanceResult');
    if (!nick) { resultDiv.innerHTML = '<p class="error">Введите ник</p>'; return; }
    try {
        const data = await apiCall('GET', `/api/balance/${encodeURIComponent(nick)}`);
        resultDiv.innerHTML = `<p>${data.nickname}: <strong>${data.balance}</strong> ${COIN_ICON}</p>`;
    } catch (e) {
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

async function transfer() {
    const receiver = document.getElementById('receiverNick').value;
    const amount = parseInt(document.getElementById('transferAmount').value);
    const resultDiv = document.getElementById('transferResult');
    if (!receiver || !amount) { resultDiv.innerHTML = '<p class="error">Заполните все поля</p>'; return; }
    if (amount < 1) { resultDiv.innerHTML = '<p class="error">Сумма >= 1</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/transfer', { receiver_nick: receiver, amount });
        resultDiv.innerHTML = `<p class="success">✅ Переведено ${data.amount} ${COIN_ICON} игроку ${data.receiver}. Ваш баланс: ${data.new_balance} ${COIN_ICON}</p>`;
        loadMyBalance(); loadTop();
    } catch (e) { resultDiv.innerHTML = `<p class="error">${e.message}</p>`; }
}

// Слоты
function startSlotAnimation() {
    const slotMachine = document.getElementById('slotMachine');
    const slotResult = document.getElementById('slotResult');
    slotMachine.style.display = 'flex';
    slotResult.innerHTML = '🎲 Крутим...';
    
    document.querySelectorAll('.slot-reel').forEach(r => r.classList.add('slot-spinning'));
    
    let spins = 0;
    slotInterval = setInterval(() => {
        document.getElementById('slot1').innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
        document.getElementById('slot2').innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
        document.getElementById('slot3').innerHTML = `<img src="/static/slots/${SLOT_SYMBOLS[Math.floor(Math.random() * SLOT_SYMBOLS.length)]}.png" alt="">`;
        spins++;
        if (spins >= 15) {
            clearInterval(slotInterval);
            document.querySelectorAll('.slot-reel').forEach(r => r.classList.remove('slot-spinning'));
        }
    }, 100);
}

function stopSlotAnimation(prize) {
    if (slotInterval) { clearInterval(slotInterval); slotInterval = null; }
    document.querySelectorAll('.slot-reel').forEach(r => r.classList.remove('slot-spinning'));
    
    let symbols;
    if (prize >= 15) symbols = ['diamond', 'diamond', 'diamond'];
    else if (prize >= 8) symbols = ['seven', 'seven', 'cherry'];
    else if (prize >= 4) symbols = ['grapes', 'grapes', 'lemon'];
    else symbols = ['cherry', 'lemon', 'orange'];
    
    document.getElementById('slot1').innerHTML = `<img src="/static/slots/${symbols[0]}.png" alt="">`;
    document.getElementById('slot2').innerHTML = `<img src="/static/slots/${symbols[1]}.png" alt="">`;
    document.getElementById('slot3').innerHTML = `<img src="/static/slots/${symbols[2]}.png" alt="">`;
    
    document.getElementById('slotResult').innerHTML = prize >= 15 ? `🎉 ДЖЕКПОТ! ${prize} ${COIN_ICON}` : `✨ Выигрыш: ${prize} ${COIN_ICON}`;
}

async function playLottery() {
    const resultDiv = document.getElementById('lotteryResult');
    startSlotAnimation();
    try {
        const data = await apiCall('POST', '/api/lottery');
        setTimeout(() => {
            stopSlotAnimation(data.prize);
            resultDiv.innerHTML = `<p class="success">🎉 Выигрыш: ${data.prize} ${COIN_ICON}! Новый баланс: ${data.new_balance} ${COIN_ICON}</p>`;
            loadMyBalance(); loadTop();
        }, 1500);
    } catch (e) {
        clearInterval(slotInterval);
        document.getElementById('slotMachine').style.display = 'none';
        resultDiv.innerHTML = `<p class="error">${e.message}</p>`;
    }
}

// Банк
function showBankTab(tab) {
    document.querySelectorAll('.bank-tab').forEach(t => t.style.display = 'none');
    document.getElementById(tab + 'Tab').style.display = 'block';
    document.querySelectorAll('#bankSection .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
}

async function createDeposit() {
    const amount = parseInt(document.getElementById('depositAmount').value);
    const resultDiv = document.getElementById('depositResult');
    if (!amount || amount < 10) { resultDiv.innerHTML = '<p class="error">Минимальная сумма: 10</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/deposit', { amount });
        resultDiv.innerHTML = `<p class="success">✅ Вклад создан! ID: ${data.deposit_id}</p>`;
        loadMyBalance(); loadMyDeposits();
    } catch (e) { resultDiv.innerHTML = `<p class="error">${e.message}</p>`; }
}

async function loadMyDeposits() {
    try {
        const deposits = await apiCall('GET', '/api/deposits');
        document.getElementById('withdrawSelect').innerHTML = deposits.map(d => `<option value="${d.deposit_id}">ID ${d.deposit_id}: ${d.amount} → ${d.total} (${new Date(d.mature_at).toLocaleDateString()})</option>`).join('');
    } catch (e) {}
}

async function withdrawDeposit() {
    const depositId = document.getElementById('withdrawSelect').value;
    if (!depositId) return;
    try {
        const data = await apiCall('POST', '/api/withdraw', { deposit_id: parseInt(depositId) });
        document.getElementById('withdrawResult').innerHTML = `<p class="success">✅ Получено ${data.amount} ${COIN_ICON}</p>`;
        loadMyBalance(); loadMyDeposits();
    } catch (e) { document.getElementById('withdrawResult').innerHTML = `<p class="error">${e.message}</p>`; }
}

async function loadMyLoans() {
    try {
        const loans = await apiCall('GET', '/api/loans');
        document.getElementById('repaySelect').innerHTML = loans.map(l => `<option value="${l.loan_id}">ID ${l.loan_id}: долг ${l.remaining}/${l.total} (${new Date(l.due_at).toLocaleDateString()})</option>`).join('');
    } catch (e) {}
}

async function createLoan() {
    const amount = parseInt(document.getElementById('loanAmount').value);
    if (!amount || amount <= 0) { document.getElementById('loanResult').innerHTML = '<p class="error">Введите сумму</p>'; return; }
    try {
        const data = await apiCall('POST', '/api/loan', { amount });
        document.getElementById('loanResult').innerHTML = `<p class="success">✅ Заём выдан! ID: ${data.loan_id}</p>`;
        loadMyBalance(); loadMyLoans();
    } catch (e) { document.getElementById('loanResult').innerHTML = `<p class="error">${e.message}</p>`; }
}

async function repayLoan() {
    const loanId = parseInt(document.getElementById('repaySelect').value);
    const amount = document.getElementById('repayAmount').value;
    if (!loanId) return;
    try {
        const body = { loan_id: loanId };
        if (amount) body.amount = parseInt(amount);
        const data = await apiCall('POST', '/api/repay', body);
        document.getElementById('repayResult').innerHTML = `<p class="success">✅ ${data.message}</p>`;
        loadMyBalance(); loadMyLoans();
    } catch (e) { document.getElementById('repayResult').innerHTML = `<p class="error">${e.message}</p>`; }
}

async function loadTop() {
    try {
        const data = await apiCall('GET', '/api/top');
        let html = '';
        data.players.forEach((p, i) => html += `<div class="top-player">${i+1}. ${p.name} — ${p.balance} ${COIN_ICON}</div>`);
        html += `<div class="stats-grid" style="margin-top:15px">
            <div class="stat-item"><div class="stat-value">${data.stats.total_players}</div><div class="stat-label">Игроков</div></div>
            <div class="stat-item"><div class="stat-value">${data.stats.total_tokens}</div><div class="stat-label">Монет</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.total_deposits}</div><div class="stat-label">Вкладов</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.total_loans}</div><div class="stat-label">Займов</div></div>
        </div>`;
        document.getElementById('topResult').innerHTML = html;
    } catch (e) {}
}

async function loadStats() {
    try {
        const data = await apiCall('GET', '/api/stats');
        document.getElementById('statsResult').innerHTML = `<div class="stats-grid">
            <div class="stat-item"><div class="stat-value">${data.stats.total_players}</div><div class="stat-label">Игроков</div></div>
            <div class="stat-item"><div class="stat-value">${data.stats.total_tokens}</div><div class="stat-label">Монет</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.total_deposits}</div><div class="stat-label">Вкладов</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.total_loans}</div><div class="stat-label">Займов</div></div>
            <div class="stat-item"><div class="stat-value">${data.bank.liquidity}</div><div class="stat-label">Свободно</div></div>
        </div>`;
    } catch (e) {}
}

// Чат
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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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

// ---------- Соцсеть ----------

// Превью изображения
document.addEventListener('change', function(e) {
    if (e.target.id === 'postImage') {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('imagePreview').innerHTML = `<img src="${e.target.result}" alt="Preview">`;
            };
            reader.readAsDataURL(file);
        } else {
            document.getElementById('imagePreview').innerHTML = '';
        }
    }
});

async function createPost() {
    const content = document.getElementById('postContent').value.trim();
    if (!content) {
        alert('Введите текст поста');
        return;
    }
    const imageInput = document.getElementById('postImage');
    const formData = new FormData();
    formData.append('content', content);
    if (imageInput.files[0]) {
        formData.append('image', imageInput.files[0]);
    }
    try {
        await apiCall('POST', '/api/social/posts', formData);
        document.getElementById('postContent').value = '';
        imageInput.value = '';
        document.getElementById('imagePreview').innerHTML = '';
        loadFeed();
    } catch (e) {
        alert(e.message);
    }
}

async function loadFeed() {
    if (!currentUser?.player) return;
    try {
        const posts = await apiCall('GET', '/api/social/posts/feed');
        renderPosts(posts, 'feedContainer');
    } catch (e) {
        console.error(e);
    }
}

function renderPosts(posts, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (posts.length === 0) {
        container.innerHTML = '<p>Пока нет постов. Подпишитесь на других игроков!</p>';
        return;
    }
    let html = '';
    posts.forEach(post => {
        html += renderPost(post);
    });
    container.innerHTML = html;
    
    // Привязываем обработчики после рендера
    posts.forEach(post => {
        const likeBtn = document.getElementById(`like-btn-${post.id}`);
        if (likeBtn) {
            likeBtn.addEventListener('click', () => toggleLike(post.id));
        }
        const commentBtn = document.getElementById(`comment-btn-${post.id}`);
        if (commentBtn) {
            commentBtn.addEventListener('click', () => toggleComments(post.id));
        }
    });
}

function renderPost(post) {
    const likedClass = post.liked_by_me ? 'liked' : '';
    const imageHtml = post.image_url ? `<img src="${post.image_url}" class="post-image" alt="Post image">` : '';
    return `
        <div class="post" data-post-id="${post.id}">
            <div class="post-header">
                <img src="${post.author_avatar || '/static/default-avatar.png'}" class="post-avatar" alt="">
                <div class="post-author-info">
                    <div class="post-author-name">${post.author_discord_username}</div>
                    <div class="post-author-nick">@${post.author_nickname}</div>
                    <div class="post-time">${new Date(post.created_at).toLocaleString()}</div>
                </div>
            </div>
            <div class="post-content">${escapeHtml(post.content)}</div>
            ${imageHtml}
            <div class="post-actions">
                <button id="like-btn-${post.id}" class="post-action-btn ${likedClass}">
                    ❤️ <span id="like-count-${post.id}">${post.like_count}</span>
                </button>
                <button id="comment-btn-${post.id}" class="post-action-btn">
                    💬 <span>${post.comment_count}</span>
                </button>
            </div>
            <div id="comments-${post.id}" class="comments-section" style="display:none;"></div>
        </div>
    `;
}

async function toggleLike(postId) {
    try {
        const data = await apiCall('POST', `/api/social/posts/${postId}/like`);
        const likeCountSpan = document.getElementById(`like-count-${postId}`);
        const likeBtn = document.getElementById(`like-btn-${postId}`);
        likeCountSpan.textContent = data.like_count;
        if (data.action === 'liked') {
            likeBtn.classList.add('liked');
        } else {
            likeBtn.classList.remove('liked');
        }
    } catch (e) {
        alert(e.message);
    }
}

async function toggleComments(postId) {
    const commentsDiv = document.getElementById(`comments-${postId}`);
    if (commentsDiv.style.display === 'none') {
        // Загружаем комментарии
        try {
            const comments = await apiCall('GET', `/api/social/posts/${postId}/comments`);
            let html = '<h4>Комментарии</h4>';
            comments.forEach(c => {
                html += `
                    <div class="comment">
                        <img src="${c.author_avatar || '/static/default-avatar.png'}" class="comment-avatar" alt="">
                        <div class="comment-content">
                            <div class="comment-author">${c.author_nickname}</div>
                            <div class="comment-text">${escapeHtml(c.content)}</div>
                        </div>
                    </div>
                `;
            });
            html += `
                <div class="comment-form" style="margin-top:12px;">
                    <textarea id="comment-input-${postId}" placeholder="Написать комментарий..."></textarea>
                    <button onclick="addComment(${postId})">Отправить</button>
                </div>
            `;
            commentsDiv.innerHTML = html;
            commentsDiv.style.display = 'block';
        } catch (e) {
            alert(e.message);
        }
    } else {
        commentsDiv.style.display = 'none';
    }
}

async function addComment(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    const content = input.value.trim();
    if (!content) return;
    try {
        await apiCall('POST', `/api/social/posts/${postId}/comments`, { content });
        input.value = '';
        // Обновить комментарии
        toggleComments(postId);
        // Обновить счетчик комментариев в посте (можно перезагрузить ленту, но проще обновить число)
        const commentBtn = document.getElementById(`comment-btn-${postId}`);
        const span = commentBtn.querySelector('span');
        const current = parseInt(span.textContent) || 0;
        span.textContent = current + 1;
    } catch (e) {
        alert(e.message);
    }
}

// Профиль
async function loadMyProfile() {
    if (!currentUser?.player) return;
    currentProfileId = currentUser.player.player_id;
    await loadProfile(currentProfileId);
}

async function loadProfile(playerId) {
    try {
        const profile = await apiCall('GET', `/api/social/profile/${playerId}`);
        const posts = await apiCall('GET', `/api/social/posts/user/${playerId}`);
        
        const isOwnProfile = currentUser?.player?.player_id === playerId;
        const followBtnHtml = isOwnProfile ? '' : `
            <button class="follow-btn ${profile.is_following ? 'unfollow' : ''}" onclick="toggleFollow('${playerId}')">
                ${profile.is_following ? 'Отписаться' : 'Подписаться'}
            </button>
        `;
        
        const bioEditHtml = isOwnProfile ? `
            <div style="margin-top:12px;">
                <textarea id="bioEdit" placeholder="О себе">${profile.bio || ''}</textarea>
                <button onclick="updateBio()">Сохранить</button>
            </div>
        ` : `<p>${profile.bio || 'Нет описания.'}</p>`;
        
        let html = `
            <div class="card">
                <div class="profile-header">
                    <img src="${profile.discord_avatar || '/static/default-avatar.png'}" class="profile-avatar" alt="">
                    <div class="profile-info">
                        <h1 class="profile-name">${profile.discord_username}</h1>
                        <p>@${profile.game_nickname}</p>
                        <div class="profile-stats">
                            <div class="profile-stat">
                                <div class="profile-stat-value">${profile.following_count}</div>
                                <div class="profile-stat-label">Подписок</div>
                            </div>
                            <div class="profile-stat">
                                <div class="profile-stat-value">${profile.followers_count}</div>
                                <div class="profile-stat-label">Подписчиков</div>
                            </div>
                        </div>
                        ${followBtnHtml}
                    </div>
                </div>
                <div class="profile-bio">
                    <h3>О себе</h3>
                    ${bioEditHtml}
                </div>
            </div>
            <div id="profilePosts"></div>
        `;
        
        document.getElementById('profileContent').innerHTML = html;
        renderPosts(posts, 'profilePosts');
    } catch (e) {
        alert('Ошибка загрузки профиля: ' + e.message);
    }
}

async function updateBio() {
    const bio = document.getElementById('bioEdit').value;
    try {
        await apiCall('POST', '/api/social/profile/update', { bio });
        alert('Биография обновлена');
        loadMyProfile();
    } catch (e) {
        alert(e.message);
    }
}

async function toggleFollow(targetId) {
    const btn = event.target;
    const isFollowing = btn.textContent.includes('Отписаться');
    try {
        if (isFollowing) {
            await apiCall('DELETE', `/api/social/follow/${targetId}`);
        } else {
            await apiCall('POST', `/api/social/follow/${targetId}`);
        }
        // Обновить профиль
        loadProfile(targetId);
    } catch (e) {
        alert(e.message);
    }
}

// Поиск соцсети
async function searchSocial() {
    const query = document.getElementById('socialSearchInput').value.trim();
    if (query.length < 2) {
        alert('Введите минимум 2 символа');
        return;
    }
    try {
        const results = await apiCall('GET', `/api/social/search?q=${encodeURIComponent(query)}`);
        const container = document.getElementById('searchResults');
        if (results.length === 0) {
            container.innerHTML = '<p>Ничего не найдено</p>';
            return;
        }
        let html = '';
        results.forEach(user => {
            html += `
                <div class="search-result-item">
                    <img src="${user.discord_avatar || '/static/default-avatar.png'}" class="search-avatar" alt="">
                    <div style="flex:1;">
                        <div><strong>${user.game_nickname}</strong> (${user.discord_username})</div>
                        <div style="font-size:0.8rem;">${user.bio || ''}</div>
                    </div>
                    <button onclick="window.location.href='/profile/${user.player_id}'">Профиль</button>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        alert(e.message);
    }
}