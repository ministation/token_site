let currentForumCategory = 'news';
let currentForumTopic = '';

const FORUM_HINTS = {
    news: 'Новости проекта от администрации',
    forum: 'Общие темы и вопросы сообщества',
    discussion: 'Обсуждения по выбранной теме',
};

document.addEventListener('change', function(e) {
    if (e.target.id === 'postImage' || e.target.id === 'postVideo') {
        const file = e.target.files[0];
        const preview = document.getElementById('imagePreview');
        if (!preview) return;
        if (file) {
            if (file.type.startsWith('video/')) {
                const url = URL.createObjectURL(file);
                preview.innerHTML = `<video src="${url}" class="post-video-preview" controls playsinline></video>`;
            } else {
                const reader = new FileReader();
                reader.onload = function(ev) {
                    preview.innerHTML = '<img src="' + ev.target.result + '" alt="Preview">';
                };
                reader.readAsDataURL(file);
            }
        } else if (!document.getElementById('postImage')?.files?.[0] && !document.getElementById('postVideo')?.files?.[0]) {
            preview.innerHTML = '';
        }
    }
});

function updatePostFormFields() {
    const category = document.getElementById('postCategory')?.value || 'forum';
    const topicRow = document.getElementById('postTopicRow');
    if (topicRow) {
        topicRow.style.display = category === 'discussion' ? '' : 'none';
    }
}

function syncPostFormWithForum() {
    const categorySelect = document.getElementById('postCategory');
    if (!categorySelect) return;
    let category = currentForumCategory;
    if (category === 'news' && !currentUser?.is_admin) {
        category = 'forum';
    }
    categorySelect.value = category;
    updatePostFormFields();
    if (currentForumCategory === 'discussion') {
        const topicSelect = document.getElementById('postTopic');
        if (topicSelect && currentForumTopic) {
            topicSelect.value = currentForumTopic;
        }
    }
}

function updateForumStaffOptions() {
    const newsOption = document.getElementById('postCategoryNews');
    if (newsOption) {
        const canNews = currentUser?.is_admin;
        newsOption.hidden = !canNews;
        if (!canNews && document.getElementById('postCategory')?.value === 'news') {
            document.getElementById('postCategory').value = 'forum';
            updatePostFormFields();
        }
    }
}

function updateFeedCreateBtn() {
    const btn = document.getElementById('feedCreateBtn');
    if (!btn) return;
    const section = currentForumCategory || 'news';
    btn.dataset.section = section;
    const labels = {
        news: 'Создать новость',
        forum: 'Создать публикацию',
        discussion: 'Создать обсуждение',
    };
    btn.innerHTML = `<i class="fa-solid fa-pen"></i> ${labels[section] || 'Создать публикацию'}`;
}

function openCreatePost() {
    if (!currentUser?.authenticated) {
        alert('Войдите через Discord, чтобы публиковать');
        return;
    }
    if (currentForumCategory === 'news' && !currentUser?.is_admin) {
        alert('Новости может публиковать только администрация');
        return;
    }
    const card = document.getElementById('createPostCard');
    if (!card) return;
    syncPostFormWithForum();
    card.hidden = false;
    card.style.display = 'block';
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    document.getElementById('postContent')?.focus();
}

function closeCreatePost() {
    const card = document.getElementById('createPostCard');
    if (!card) return;
    card.hidden = true;
    card.style.display = 'none';
}

function switchForumSection(category, btn) {
    currentForumCategory = category;
    currentForumTopic = '';
    document.querySelectorAll('.forum-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.querySelectorAll('.forum-topic-tab').forEach(b => {
        b.classList.toggle('active', !b.dataset.topic);
    });
    const topicTabs = document.getElementById('forumTopicTabs');
    if (topicTabs) topicTabs.hidden = category !== 'discussion';
    const hint = document.getElementById('forumSectionHint');
    if (hint) hint.textContent = FORUM_HINTS[category] || '';
    closeCreatePost();
    syncPostFormWithForum();
    updateFeedCreateBtn();
    if (typeof updateAuthUI === 'function') updateAuthUI();
    loadFeed().then(() => {
        if (typeof markFeedCategorySeen === 'function') markFeedCategorySeen(category);
    });
}

function switchForumTopic(topic, btn) {
    currentForumTopic = topic;
    document.querySelectorAll('.forum-topic-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const topicSelect = document.getElementById('postTopic');
    if (topicSelect && topic) topicSelect.value = topic;
    loadFeed();
}

async function createPost() {
    if (!currentUser?.authenticated) {
        alert('Войдите через Discord, чтобы публиковать');
        return;
    }
    const content = document.getElementById('postContent').value.trim();
    if (!content) { alert('Введите текст'); return; }
    const category = document.getElementById('postCategory')?.value || currentForumCategory;
    const topic = category === 'discussion'
        ? (document.getElementById('postTopic')?.value || 'other')
        : '';
    const title = document.getElementById('postTitle')?.value.trim() || '';
    const imageInput = document.getElementById('postImage');
    const videoInput = document.getElementById('postVideo');
    const formData = new FormData();
    formData.append('content', content);
    formData.append('category', category);
    formData.append('topic', topic);
    formData.append('title', title);
    if (imageInput.files[0]) formData.append('image', imageInput.files[0]);
    if (videoInput.files[0]) formData.append('video', videoInput.files[0]);
    try {
        await apiCall('POST', '/api/social/posts', formData);
        document.getElementById('postContent').value = '';
        document.getElementById('postTitle').value = '';
        imageInput.value = '';
        videoInput.value = '';
        document.getElementById('imagePreview').innerHTML = '';
        closeCreatePost();
        if (category !== currentForumCategory) {
            const tab = document.querySelector(`.forum-tab[data-forum="${category}"]`);
            switchForumSection(category, tab);
        } else {
            loadFeed();
        }
    } catch (e) { alert(e.message); }
}

async function loadFeed() {
    const container = document.getElementById('feedContainer');
    if (!container) return;
    container.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
        const params = new URLSearchParams({ category: currentForumCategory });
        if (currentForumCategory === 'discussion' && currentForumTopic) {
            params.set('topic', currentForumTopic);
        }
        const res = await fetch('/api/social/posts/feed?' + params);
        if (!res.ok) throw new Error('Ошибка загрузки');
        const posts = await res.json();
        renderPosts(posts, 'feedContainer');
    } catch (e) {
        container.innerHTML = '<p class="empty-state">Не удалось загрузить раздел</p>';
    }
}

function forumEmptyMessage() {
    if (currentForumCategory === 'news') {
        return 'Новостей пока нет';
    }
    if (currentForumCategory === 'discussion' && currentForumTopic) {
        return 'В этой теме пока нет обсуждений';
    }
    if (currentForumCategory === 'discussion') {
        return 'Обсуждений пока нет';
    }
    return 'Записей пока нет';
}

function renderPosts(posts, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!posts.length) {
        container.innerHTML = `<p class="empty-state">${forumEmptyMessage()}</p>`;
        return;
    }
    container.innerHTML = posts.map(post => renderPost(post)).join('');
}

function renderPostBadges(post) {
    if (post.category === 'news') return '';
    const parts = [];
    if (post.category_label) {
        parts.push(`<span class="forum-badge forum-badge-${post.category || 'forum'}">${escapeHtml(post.category_label)}</span>`);
    }
    if (post.topic_label) {
        parts.push(`<span class="forum-badge forum-badge-topic">${escapeHtml(post.topic_label)}</span>`);
    }
    return parts.length ? `<div class="forum-badges">${parts.join('')}</div>` : '';
}

function renderPostMedia(post) {
    let html = '';
    if (post.video_url) {
        html += `<video src="${post.video_url}" class="post-video" controls playsinline preload="metadata"></video>`;
    }
    if (post.image_url) {
        html += `<img src="${post.image_url}" class="post-image" alt="">`;
    }
    return html;
}

function renderPost(post) {
    if (post.category === 'news') return renderNewsPost(post);

    const likedClass = post.liked_by_me ? 'liked' : '';
    const mediaHtml = renderPostMedia(post);
    const avatarUrl = post.author_avatar || '/static/default_avatar.png';
    const canInteract = currentUser?.authenticated;
    const titleHtml = post.title
        ? `<h3 class="forum-post-title">${escapeHtml(post.title)}</h3>`
        : '';
    const authorName = typeof profileLink === 'function' && post.author_player_id
        ? profileLink(post.author_player_id, post.author_discord_username || 'Участник', 'post-author-link')
        : escapeHtml(post.author_discord_username || 'Неизвестный');
    const likeBtn = canInteract
        ? `<button onclick="toggleLike(${post.id})" class="post-action-btn ${likedClass}">
                <i class="fa-solid fa-heart"></i><span id="like-count-${post.id}">${post.like_count}</span>
           </button>`
        : `<span class="post-action-btn disabled"><i class="fa-solid fa-heart"></i><span>${post.like_count}</span></span>`;
    const commentBtn = canInteract
        ? `<button onclick="toggleComments(${post.id})" class="post-action-btn">
                <i class="fa-solid fa-comment"></i><span id="comment-count-${post.id}">${post.comment_count}</span>
           </button>`
        : `<span class="post-action-btn disabled"><i class="fa-solid fa-comment"></i><span>${post.comment_count}</span></span>`;
    const canDelete = currentUser?.is_admin || (canInteract && post.author_player_id === currentUser?.social_id);
    const deleteBtn = canDelete
        ? `<button onclick="deletePost(${post.id})" class="post-action-btn post-delete-btn" title="Удалить">
                <i class="fa-solid fa-trash"></i>
           </button>`
        : '';
    const avatarHtml = typeof chatAvatarHtml === 'function'
        ? chatAvatarHtml(avatarUrl, 'post-avatar', post.author_presence || 'offline')
        : `<img src="${escapeHtml(avatarUrl)}" class="post-avatar" alt="" onerror="this.src='/static/default_avatar.png'">`;
    return `
        <div class="post card forum-post" data-post-id="${post.id}">
            ${renderPostBadges(post)}
            ${titleHtml}
            <div class="post-header">
                <button type="button" class="post-avatar-btn" onclick="openProfile(${JSON.stringify(post.author_player_id)})">
                    ${avatarHtml}
                </button>
                <div class="post-author-info">
                    <div class="post-author-name">${authorName}</div>
                    <div class="post-author-nick">${typeof profileLink === 'function' && post.author_player_id
                        ? profileLink(post.author_player_id, '@' + (post.author_nickname || 'unknown'), 'post-author-nick-link')
                        : '@' + escapeHtml(post.author_nickname || 'unknown')}</div>
                    <div class="post-time">${new Date(post.created_at).toLocaleString()}</div>
                </div>
            </div>
            <div class="post-content">${formatMessageContent(post.content)}</div>
            ${mediaHtml}
            <div class="post-actions">
                ${likeBtn}
                ${commentBtn}
                ${deleteBtn}
            </div>
            <div id="comments-${post.id}" class="comments-section" style="display:none;"></div>
        </div>
    `;
}

function renderNewsPost(post) {
    const mediaHtml = renderPostMedia(post);
    const canInteract = currentUser?.authenticated;
    const titleHtml = post.title
        ? `<h3 class="forum-post-title news-post-title">${escapeHtml(post.title)}</h3>`
        : '';
    const date = new Date(post.created_at).toLocaleString('ru-RU', {
        day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    const likeBtn = canInteract
        ? `<button onclick="toggleLike(${post.id})" class="post-action-btn ${post.liked_by_me ? 'liked' : ''}">
                <i class="fa-solid fa-heart"></i><span id="like-count-${post.id}">${post.like_count}</span>
           </button>`
        : `<span class="post-action-btn disabled"><i class="fa-solid fa-heart"></i><span>${post.like_count}</span></span>`;
    const commentBtn = canInteract
        ? `<button onclick="toggleComments(${post.id})" class="post-action-btn">
                <i class="fa-solid fa-comment"></i><span id="comment-count-${post.id}">${post.comment_count}</span>
           </button>`
        : `<span class="post-action-btn disabled"><i class="fa-solid fa-comment"></i><span>${post.comment_count}</span></span>`;
    const deleteBtn = currentUser?.is_admin
        ? `<button onclick="deletePost(${post.id})" class="post-action-btn post-delete-btn" title="Удалить">
                <i class="fa-solid fa-trash"></i></button>`
        : '';
    return `
        <article class="post card forum-post forum-post-news" data-post-id="${post.id}">
            <div class="news-post-header">
                <span class="news-post-label"><i class="fa-solid fa-bullhorn"></i> Новость</span>
                <time class="news-post-date">${date}</time>
            </div>
            ${titleHtml}
            <div class="post-content news-post-content">${formatMessageContent(post.content)}</div>
            ${mediaHtml}
            <div class="post-actions">
                ${likeBtn}
                ${commentBtn}
                ${deleteBtn}
            </div>
            <div id="comments-${post.id}" class="comments-section" style="display:none;"></div>
        </article>
    `;
}

async function toggleLike(postId) {
    if (!currentUser?.authenticated) return;
    try {
        const data = await apiCall('POST', '/api/social/posts/' + postId + '/like');
        const span = document.getElementById('like-count-' + postId);
        if (span) span.textContent = data.like_count;
        const btn = document.querySelector('.post[data-post-id="' + postId + '"] .post-action-btn');
        if (btn) btn.classList.toggle('liked', data.action === 'liked');
    } catch (e) {}
}

async function toggleComments(postId) {
    if (!currentUser?.authenticated) {
        alert('Войдите, чтобы комментировать');
        return;
    }
    const div = document.getElementById('comments-' + postId);
    if (!div) return;
    if (div.style.display === 'none') {
        try {
            const comments = await apiCall('GET', '/api/social/posts/' + postId + '/comments');
            let html = '<h4>Комментарии</h4>';
            comments.forEach(c => {
                const author = typeof profileLink === 'function' && c.author_player_id
                    ? profileLink(c.author_player_id, c.game_nickname || c.author_nickname || 'Игрок', 'comment-author-link')
                    : escapeHtml(c.game_nickname || c.author_nickname || 'Игрок');
                html += '<div class="comment">' +
                    (typeof chatAvatarHtml === 'function'
                        ? chatAvatarHtml(c.author_avatar, 'comment-avatar', c.author_presence || 'offline')
                        : `<img src="${escapeHtml(c.author_avatar || '/static/default_avatar.png')}" class="comment-avatar" alt="">`) +
                    '<div class="comment-content"><div class="comment-author">' + author + '</div>' +
                    '<div class="comment-text">' + escapeHtml(c.content) + '</div></div></div>';
            });
            html += '<textarea id="comment-input-' + postId + '" placeholder="Комментарий..."></textarea>' +
                '<button onclick="addComment(' + postId + ')">Отправить</button>';
            div.innerHTML = html;
            div.style.display = 'block';
        } catch (e) {}
    } else {
        div.style.display = 'none';
    }
}

async function addComment(postId) {
    const input = document.getElementById('comment-input-' + postId);
    if (!input) return;
    const content = input.value.trim();
    if (!content) return;
    try {
        await apiCall('POST', '/api/social/posts/' + postId + '/comments', { content });
        input.value = '';
        toggleComments(postId);
        toggleComments(postId);
        const span = document.getElementById('comment-count-' + postId);
        if (span) span.textContent = parseInt(span.textContent) + 1;
    } catch (e) {}
}

async function deletePost(postId) {
    if (!confirm('Удалить эту запись?')) return;
    try {
        await apiCall('DELETE', '/api/social/posts/' + postId);
        const el = document.querySelector('.post[data-post-id="' + postId + '"]');
        if (el) el.remove();
    } catch (e) {
        alert(e.message);
    }
}
