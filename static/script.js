const API_BASE = '';
const COIN_ICON = '<img src="/static/coin.png" class="coin-icon" alt="">';

// Глобальное состояние приложения
const app = {
    currentUser: null,
    currentPage: 'home',
    profileId: null,
    conversationId: null,
    feedPage: 0,
    feedHasMore: true,
    isLoading: false,
    pollingInterval: null,
    slotInterval: null,
    transferCooldowns: {},

    // Инициализация
    async init() {
        await this.checkAuth();
        this.setupNavigation();
        this.setupThemeToggle();
        this.setupModals();
        this.startPolling();
        this.loadStats();
        if (this.currentUser?.authenticated) {
            this.loadMiniBalance();
            if (this.currentUser.player) {
                this.loadOnlineFriends();
            }
        }
        // Обработка начального URL
        this.handleRouting();
        window.addEventListener('popstate', () => this.handleRouting());
    },

    // Аутентификация
    async checkAuth() {
        try {
            const res = await fetch(`${API_BASE}/api/me`);
            const data = await res.json();
            this.currentUser = data;
            this.updateAuthUI();
        } catch (e) {
            console.error('Auth check failed:', e);
        }
    },

    updateAuthUI() {
        const userInfoDiv = document.getElementById('sidebarUserInfo');
        const loginBtn = document.getElementById('loginBtn');
        if (this.currentUser?.authenticated) {
            const player = this.currentUser.player;
            const avatar = this.currentUser.avatar || '/static/default-avatar.png';
            const username = this.currentUser.username || 'Гость';
            userInfoDiv.innerHTML = `
                <img src="${avatar}" class="user-avatar" alt="">
                <span class="user-name">${username}</span>
            `;
            if (loginBtn) loginBtn.style.display = 'none';
            // Показать баланс в сайдбаре
            if (player) {
                document.getElementById('miniBalanceCard').style.display = 'block';
                this.loadMiniBalance();
            } else {
                document.getElementById('miniBalanceCard').style.display = 'none';
            }
        } else {
            userInfoDiv.innerHTML = `
                <button class="btn btn-primary" onclick="app.login()">Войти через Discord</button>
            `;
            document.getElementById('miniBalanceCard').style.display = 'none';
        }
    },

    login() {
        window.location.href = `${API_BASE}/login`;
    },

    logout() {
        window.location.href = `${API_BASE}/logout`;
    },

    // Навигация
    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const page = item.dataset.page;
                this.navigateTo(page);
            });
        });
        // Обработка кликов по внутренним ссылкам (SPA)
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (!link) return;
            const href = link.getAttribute('href');
            if (href && href.startsWith('/') && !href.startsWith('/static') && !href.startsWith('/api')) {
                e.preventDefault();
                this.navigateTo(href);
            }
        });
    },

    navigateTo(pageOrUrl) {
        let page = pageOrUrl;
        let profileId = null;
        if (pageOrUrl.startsWith('/profile/')) {
            page = 'profile';
            profileId = pageOrUrl.split('/').pop();
        } else if (pageOrUrl === '/messages') {
            page = 'messages';
        } else if (pageOrUrl === '/') {
            page = 'home';
        }
        this.currentPage = page;
        this.profileId = profileId;
        // Обновить URL
        const url = page === 'profile' ? `/profile/${profileId}` : `/${page === 'home' ? '' : page}`;
        window.history.pushState({}, '', url);
        this.loadPage(page);
        // Обновить активный пункт меню
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === page);
        });
    },

    async loadPage(page) {
        const container = document.getElementById(`page-${page}`);
        if (!container) return;
        // Показать контейнер, скрыть остальные
        document.querySelectorAll('.page-container').forEach(c => c.classList.remove('active'));
        container.classList.add('active');
        // Загрузить содержимое в зависимости от страницы
        switch (page) {
            case 'home':
                await this.renderFeed();
                break;
            case 'messages':
                await this.renderMessages();
                break;
            case 'friends':
                await this.renderFriends();
                break;
            case 'wallet':
                await this.renderWallet();
                break;
            case 'bank':
                await this.renderBank();
                break;
            case 'lottery':
                await this.renderLottery();
                break;
            case 'search':
                await this.renderSearch();
                break;
            case 'profile':
                await this.renderProfile(this.profileId || this.currentUser?.player?.player_id);
                break;
        }
    },

    handleRouting() {
        const path = window.location.pathname;
        if (path === '/' || path === '') {
            this.navigateTo('home');
        } else if (path === '/messages') {
            this.navigateTo('messages');
        } else if (path.startsWith('/profile/')) {
            const profileId = path.split('/').pop();
            this.navigateTo(`/profile/${profileId}`);
        } else {
            // По умолчанию - главная
            this.navigateTo('home');
        }
    },

    // Загрузка статистики для правой панели
    async loadStats() {
        try {
            const data = await this.apiCall('GET', '/api/stats');
            document.getElementById('statPlayers').textContent = data.stats.total_players;
            document.getElementById('statTokens').textContent = data.stats.total_tokens;
            document.getElementById('statDeposits').textContent = data.bank.total_deposits;
            document.getElementById('statLoans').textContent = data.bank.total_loans;
        } catch (e) {}
    },

    async loadMiniBalance() {
        if (!this.currentUser?.player) return;
        try {
            const data = await this.apiCall('GET', '/api/balance');
            document.getElementById('miniBalance').innerHTML = `${data.balance} ${COIN_ICON}`;
        } catch (e) {}
    },

    async loadOnlineFriends() {
        // В реальном проекте здесь был бы запрос к API для получения друзей онлайн
        document.getElementById('onlineFriendsList').innerHTML = '<p class="text-secondary">Скоро будет доступно</p>';
    },

    // Уведомления
    startPolling() {
        this.pollingInterval = setInterval(async () => {
            if (!this.currentUser?.player) return;
            try {
                const data = await this.apiCall('GET', '/api/notifications');
                const badge = document.getElementById('unreadMessagesBadge');
                if (data.unread_messages > 0) {
                    badge.textContent = data.unread_messages;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            } catch (e) {}
        }, 10000);
    },

    // API вызов
    async apiCall(method, url, body = null) {
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
    },

    // Рендер страниц
    async renderFeed() {
        const container = document.getElementById('page-home');
        container.innerHTML = `
            <div class="card">
                <h3>Новый пост</h3>
                <textarea id="newPostContent" placeholder="Что у вас нового?"></textarea>
                <input type="file" id="newPostImage" accept="image/*" style="display:none;">
                <div class="flex gap-2">
                    <button class="btn btn-primary" onclick="app.createPost()">Опубликовать</button>
                    <button class="btn" onclick="document.getElementById('newPostImage').click()">📷 Фото</button>
                </div>
                <div id="imagePreview" class="mt-4"></div>
            </div>
            <div id="feedContainer"></div>
            <div id="feedLoading" style="display:none;">Загрузка...</div>
        `;
        this.feedPage = 0;
        this.feedHasMore = true;
        await this.loadMoreFeed();
        // Бесконечная прокрутка
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && this.feedHasMore && !this.isLoading) {
                this.loadMoreFeed();
            }
        });
        observer.observe(document.getElementById('feedLoading'));
    },

    async loadMoreFeed() {
        if (this.isLoading || !this.feedHasMore) return;
        this.isLoading = true;
        document.getElementById('feedLoading').style.display = 'block';
        try {
            const posts = await this.apiCall('GET', `/api/social/posts/feed?limit=10&offset=${this.feedPage * 10}`);
            if (posts.length < 10) this.feedHasMore = false;
            this.feedPage++;
            const container = document.getElementById('feedContainer');
            posts.forEach(post => {
                container.appendChild(this.createPostElement(post));
            });
        } catch (e) {
            console.error(e);
        } finally {
            this.isLoading = false;
            document.getElementById('feedLoading').style.display = this.feedHasMore ? 'block' : 'none';
        }
    },

    createPostElement(post) {
        const div = document.createElement('div');
        div.className = 'post';
        div.innerHTML = `
            <div class="post-header">
                <img src="${post.author_avatar || '/static/default-avatar.png'}" class="post-avatar" alt="">
                <div>
                    <div class="post-author">${post.author_discord_username}</div>
                    <div class="post-time">${new Date(post.created_at).toLocaleString()}</div>
                </div>
            </div>
            <div class="post-content">${this.escapeHtml(post.content)}</div>
            ${post.image_url ? `<img src="${post.image_url}" class="post-image" alt="">` : ''}
            <div class="post-actions">
                <span class="post-action ${post.liked_by_me ? 'liked' : ''}" onclick="app.toggleLike(${post.id}, this)">
                    ❤️ <span>${post.like_count}</span>
                </span>
                <span class="post-action" onclick="app.showComments(${post.id}, this)">
                    💬 <span>${post.comment_count}</span>
                </span>
            </div>
            <div class="comments-section" id="comments-${post.id}" style="display:none;"></div>
        `;
        return div;
    },

    async toggleLike(postId, element) {
        try {
            const data = await this.apiCall('POST', `/api/social/posts/${postId}/like`);
            element.classList.toggle('liked', data.action === 'liked');
            element.querySelector('span').textContent = data.like_count;
        } catch (e) {
            alert(e.message);
        }
    },

    async showComments(postId, element) {
        const commentsDiv = document.getElementById(`comments-${postId}`);
        if (commentsDiv.style.display === 'none') {
            try {
                const comments = await this.apiCall('GET', `/api/social/posts/${postId}/comments`);
                commentsDiv.innerHTML = comments.map(c => `
                    <div class="comment">
                        <img src="${c.author_avatar || '/static/default-avatar.png'}" class="post-avatar" style="width:32px;height:32px;">
                        <div>
                            <strong>${c.author_nickname}</strong>
                            <div>${this.escapeHtml(c.content)}</div>
                        </div>
                    </div>
                `).join('');
                commentsDiv.innerHTML += `
                    <div class="mt-4">
                        <textarea id="commentInput-${postId}" placeholder="Написать комментарий..."></textarea>
                        <button class="btn btn-primary btn-sm" onclick="app.addComment(${postId})">Отправить</button>
                    </div>
                `;
                commentsDiv.style.display = 'block';
            } catch (e) {
                alert(e.message);
            }
        } else {
            commentsDiv.style.display = 'none';
        }
    },

    async addComment(postId) {
        const input = document.getElementById(`commentInput-${postId}`);
        const content = input.value.trim();
        if (!content) return;
        try {
            await this.apiCall('POST', `/api/social/posts/${postId}/comments`, { content });
            input.value = '';
            this.showComments(postId);
            // Обновить счетчик комментариев
            const btn = document.querySelector(`.post-action[onclick*="showComments(${postId}"]`);
            if (btn) {
                const span = btn.querySelector('span');
                span.textContent = parseInt(span.textContent) + 1;
            }
        } catch (e) {
            alert(e.message);
        }
    },

    async createPost() {
        const content = document.getElementById('newPostContent').value.trim();
        if (!content) return;
        const imageInput = document.getElementById('newPostImage');
        const formData = new FormData();
        formData.append('content', content);
        if (imageInput.files[0]) formData.append('image', imageInput.files[0]);
        try {
            await this.apiCall('POST', '/api/social/posts', formData);
            document.getElementById('newPostContent').value = '';
            imageInput.value = '';
            document.getElementById('imagePreview').innerHTML = '';
            // Перезагрузить ленту
            this.feedPage = 0;
            this.feedHasMore = true;
            document.getElementById('feedContainer').innerHTML = '';
            this.loadMoreFeed();
        } catch (e) {
            alert(e.message);
        }
    },

    // Сообщения
    async renderMessages() {
        const container = document.getElementById('page-messages');
        container.innerHTML = `
            <div class="flex" style="height:600px;">
                <div style="width:300px; border-right:1px solid var(--border); padding-right:16px;">
                    <h3>Диалоги</h3>
                    <div id="conversationsList" class="conversations-list"></div>
                </div>
                <div style="flex:1; padding-left:16px;">
                    <div id="messagesContainer" class="messages-container"></div>
                    <div id="messageInputArea" style="display:none;">
                        <textarea id="messageInput" placeholder="Введите сообщение..."></textarea>
                        <button class="btn btn-primary" onclick="app.sendMessage()">Отправить</button>
                    </div>
                    <div id="noConversationSelected">Выберите диалог</div>
                </div>
            </div>
        `;
        await this.loadConversations();
    },

    async loadConversations() {
        if (!this.currentUser?.player) return;
        try {
            const conversations = await this.apiCall('GET', '/api/messages/conversations');
            const list = document.getElementById('conversationsList');
            list.innerHTML = conversations.map(c => `
                <div class="conversation-item" onclick="app.openConversation('${c.other_id}')">
                    <img src="${c.discord_avatar || '/static/default-avatar.png'}" class="conversation-avatar" alt="">
                    <div class="conversation-info">
                        <div class="conversation-name">${c.game_nickname}</div>
                        <div class="conversation-last-message">${c.unread ? `<span class="badge">${c.unread}</span>` : ''}</div>
                    </div>
                </div>
            `).join('');
        } catch (e) {}
    },

    async openConversation(playerId) {
        this.conversationId = playerId;
        document.getElementById('noConversationSelected').style.display = 'none';
        document.getElementById('messageInputArea').style.display = 'block';
        await this.loadMessages(playerId);
    },

    async loadMessages(playerId) {
        try {
            const messages = await this.apiCall('GET', `/api/messages/${playerId}`);
            const container = document.getElementById('messagesContainer');
            container.innerHTML = messages.map(m => `
                <div class="message ${m.sender_id === this.currentUser.player.player_id ? 'message-own' : ''}">
                    <div class="message-bubble">
                        <div class="message-text">${this.escapeHtml(m.message)}</div>
                        <div class="message-time">${new Date(m.created_at).toLocaleTimeString()}</div>
                    </div>
                </div>
            `).join('');
            container.scrollTop = container.scrollHeight;
        } catch (e) {}
    },

    async sendMessage() {
        if (!this.conversationId) return;
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        if (!message) return;
        try {
            await this.apiCall('POST', '/api/messages', { receiver_player_id: this.conversationId, message });
            input.value = '';
            await this.loadMessages(this.conversationId);
            await this.loadConversations();
        } catch (e) {
            alert(e.message);
        }
    },

    // Профиль
    async renderProfile(playerId) {
        const container = document.getElementById('page-profile');
        container.innerHTML = '<div class="loader">Загрузка...</div>';
        try {
            const profile = await this.apiCall('GET', `/api/social/profile/${playerId}`);
            const posts = await this.apiCall('GET', `/api/social/posts/user/${playerId}?limit=20`);
            const isOwn = this.currentUser?.player?.player_id === playerId;
            container.innerHTML = `
                <div class="card">
                    <div class="profile-header">
                        <img src="${profile.discord_avatar || '/static/default-avatar.png'}" class="profile-avatar" style="width:100px;height:100px;border-radius:50%;">
                        <div>
                            <h2>${profile.game_nickname}</h2>
                            <p>${profile.discord_username}</p>
                            <p>${profile.bio || ''}</p>
                            <div class="flex gap-4 mt-4">
                                <span><strong>${profile.following_count}</strong> подписок</span>
                                <span><strong>${profile.followers_count}</strong> подписчиков</span>
                            </div>
                            ${!isOwn ? `
                                <button class="btn btn-primary mt-4" onclick="app.toggleFollow('${playerId}', this)">
                                    ${profile.is_following ? 'Отписаться' : 'Подписаться'}
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
                <div id="profilePosts"></div>
            `;
            const postsContainer = document.getElementById('profilePosts');
            posts.forEach(post => {
                postsContainer.appendChild(this.createPostElement(post));
            });
        } catch (e) {
            container.innerHTML = `<p class="error">Ошибка загрузки профиля: ${e.message}</p>`;
        }
    },

    async toggleFollow(targetId, btn) {
        try {
            if (btn.textContent.includes('Отписаться')) {
                await this.apiCall('DELETE', `/api/social/follow/${targetId}`);
            } else {
                await this.apiCall('POST', `/api/social/follow/${targetId}`);
            }
            this.renderProfile(targetId);
        } catch (e) {
            alert(e.message);
        }
    },

    // Остальные страницы (кошелёк, банк, лотерея, поиск) — аналогично, с переносом существующей логики в новые контейнеры.
    // ...

    // Вспомогательные функции
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    setupThemeToggle() {
        const toggle = document.getElementById('themeToggle');
        const body = document.body;
        const savedTheme = localStorage.getItem('theme') || 'dark';
        body.className = savedTheme;
        toggle.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
        toggle.addEventListener('click', () => {
            const newTheme = body.className === 'dark' ? 'light' : 'dark';
            body.className = newTheme;
            localStorage.setItem('theme', newTheme);
            toggle.textContent = newTheme === 'dark' ? '☀️' : '🌙';
        });
    },

    setupModals() {
        const modal = document.getElementById('modal');
        const closeBtn = modal.querySelector('.close');
        closeBtn.addEventListener('click', () => modal.style.display = 'none');
        window.addEventListener('click', (e) => {
            if (e.target === modal) modal.style.display = 'none';
        });
    },
};

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => app.init());