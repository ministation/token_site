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

function formatForumTime(iso) {
    if (typeof formatChatTime === 'function') return formatChatTime(iso);
    if (!iso) return '';
    try {
        return new Date(iso).toLocaleString('ru-RU', {
            day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
        });
    } catch {
        return '';
    }
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

function renderPostAttach(post) {
    const mediaHtml = renderPostMedia(post);
    return mediaHtml ? `<div class="dc-attach forum-post-attach">${mediaHtml}</div>` : '';
}

function renderPostActions(post, { news = false } = {}) {
    const canInteract = currentUser?.authenticated;
    const likedClass = post.liked_by_me ? 'liked' : '';
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
    const canDelete = news
        ? !!currentUser?.is_admin
        : !!(currentUser?.is_admin || (canInteract && post.author_player_id === currentUser?.social_id));
    const deleteBtn = canDelete
        ? `<button onclick="deletePost(${post.id})" class="post-action-btn post-delete-btn" title="Удалить">
                <i class="fa-solid fa-trash"></i>
           </button>`
        : '';
    return `<div class="post-actions forum-thread-actions">${likeBtn}${commentBtn}${deleteBtn}</div>`;
}

function renderForumOpMessage(post) {
    const avatarUrl = post.author_avatar || '/static/default_avatar.png';
    const displayName = post.author_nickname || post.author_discord_username || 'Участник';
    const authorBtn = typeof profileLink === 'function' && post.author_player_id
        ? profileLink(post.author_player_id, displayName, 'dc-name')
        : `<span class="dc-name">${escapeHtml(displayName)}</span>`;
    const avatarHtml = typeof chatAvatarHtml === 'function'
        ? chatAvatarHtml(avatarUrl, 'chat-avatar dc-avatar', post.author_presence || 'offline')
        : `<img src="${escapeHtml(avatarUrl)}" class="chat-avatar dc-avatar" alt="" onerror="this.src='/static/default_avatar.png'">`;
    const textHtml = post.content
        ? `<div class="dc-content">${formatMessageContent(post.content)}</div>`
        : '';
    return `
        <div class="dc-msg forum-op-msg" data-author-id="${escapeHtml(String(post.author_player_id || ''))}">
            <div class="dc-avatar-col">${avatarHtml}</div>
            <div class="dc-body">
                <div class="dc-header">${authorBtn}<span class="dc-timestamp">${formatForumTime(post.created_at)}</span></div>
                ${textHtml}
                ${renderPostAttach(post)}
            </div>
        </div>
    `;
}

function renderCommentMessage(c) {
    const displayName = c.game_nickname || c.author_nickname || 'Игрок';
    const author = typeof profileLink === 'function' && c.author_player_id
        ? profileLink(c.author_player_id, displayName, 'dc-name')
        : `<span class="dc-name">${escapeHtml(displayName)}</span>`;
    const avatarHtml = typeof chatAvatarHtml === 'function'
        ? chatAvatarHtml(c.author_avatar, 'chat-avatar dc-avatar', c.author_presence || 'offline')
        : `<img src="${escapeHtml(c.author_avatar || '/static/default_avatar.png')}" class="chat-avatar dc-avatar" alt="">`;
    const textHtml = c.content
        ? `<div class="dc-content">${formatMessageContent(c.content)}</div>`
        : '';
    return `
        <div class="dc-msg forum-comment-msg" data-comment-id="${c.id}">
            <div class="dc-avatar-col">${avatarHtml}</div>
            <div class="dc-body">
                <div class="dc-header">${author}<span class="dc-timestamp">${formatForumTime(c.created_at)}</span></div>
                ${textHtml}
            </div>
        </div>
    `;
}

function renderCommentComposer(postId) {
    return `
        <div class="chat-composer dc-composer forum-comment-composer">
            <div class="chat-composer-main">
                <input type="text" id="comment-input-${postId}" placeholder="Написать комментарий..."
                    maxlength="1000" autocomplete="off"
                    onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();addComment(${postId});}">
            </div>
            <button type="button" class="chat-send-btn" onclick="addComment(${postId})" title="Отправить">
                <i class="fa-solid fa-paper-plane"></i>
            </button>
        </div>
    `;
}

function renderPost(post) {
    if (post.category === 'news') return renderNewsPost(post);

    const titleHtml = post.title
        ? `<h3 class="forum-post-title"><i class="fa-solid fa-hashtag" aria-hidden="true"></i> ${escapeHtml(post.title)}</h3>`
        : '';
    return `
        <div class="post card forum-post forum-post-thread" data-post-id="${post.id}">
            ${renderPostBadges(post)}
            ${titleHtml}
            <div class="dc-messages forum-thread-body">
                ${renderForumOpMessage(post)}
            </div>
            ${renderPostActions(post)}
            <div id="comments-${post.id}" class="comments-section" style="display:none;"></div>
        </div>
    `;
}

function renderNewsPost(post) {
    const mediaHtml = renderPostMedia(post);
    const titleHtml = post.title
        ? `<h3 class="forum-post-title news-post-title">${escapeHtml(post.title)}</h3>`
        : '';
    const date = new Date(post.created_at).toLocaleString('ru-RU', {
        day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    return `
        <article class="post card forum-post forum-post-news" data-post-id="${post.id}">
            <div class="news-post-header">
                <span class="news-post-label"><i class="fa-solid fa-bullhorn"></i> Новость</span>
                <time class="news-post-date">${date}</time>
            </div>
            ${titleHtml}
            <div class="post-content news-post-content">${formatMessageContent(post.content)}</div>
            ${mediaHtml}
            ${renderPostActions(post, { news: true })}
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

async function loadComments(postId) {
    const div = document.getElementById('comments-' + postId);
    if (!div) return;
    try {
        const comments = await apiCall('GET', '/api/social/posts/' + postId + '/comments');
        const listHtml = comments.length
            ? comments.map(renderCommentMessage).join('')
            : '<p class="empty-state forum-comments-empty">Пока нет комментариев</p>';
        div.innerHTML = `
            <div class="comments-section-head">Комментарии</div>
            <div class="dc-messages forum-comments">${listHtml}</div>
            ${renderCommentComposer(postId)}
        `;
        div.style.display = 'block';
        const input = document.getElementById('comment-input-' + postId);
        if (input) input.focus();
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
        await loadComments(postId);
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
        await loadComments(postId);
        const span = document.getElementById('comment-count-' + postId);
        if (span) span.textContent = parseInt(span.textContent, 10) + 1;
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
