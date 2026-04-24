document.addEventListener('change', function(e) {
    if (e.target.id === 'postImage') {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(ev) {
                document.getElementById('imagePreview').innerHTML = `<img src="${ev.target.result}" alt="Preview">`;
            };
            reader.readAsDataURL(file);
        } else {
            document.getElementById('imagePreview').innerHTML = '';
        }
    }
});

async function createPost() {
    const content = document.getElementById('postContent').value.trim();
    if (!content) { alert('Введите текст поста'); return; }
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
    } catch (e) { alert(e.message); }
}

async function loadFeed() {
    if (!currentUser?.player) return;
    try {
        const posts = await apiCall('GET', '/api/social/posts/feed');
        renderPosts(posts, 'feedContainer');
    } catch (e) { console.error(e); }
}

function renderPosts(posts, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (posts.length === 0) {
        container.innerHTML = '<p>Пока нет постов.</p>';
        return;
    }
    container.innerHTML = posts.map(post => renderPost(post)).join('');
}

function renderPost(post) {
    const likedClass = post.liked_by_me ? 'liked' : '';
    const imageHtml = post.image_url ? `<img src="${post.image_url}" class="post-image">` : '';
    const avatarUrl = post.author_avatar || '/static/default_avatar.png';
    return `
        <div class="post" data-post-id="${post.id}">
            <div class="post-header">
                <img src="${avatarUrl}" class="post-avatar" onerror="this.src='/static/default_avatar.png'">
                <div class="post-author-info">
                    <div class="post-author-name">${escapeHtml(post.author_discord_username || 'Неизвестный')}</div>
                    <div class="post-author-nick">@${escapeHtml(post.author_nickname || 'unknown')}</div>
                    <div class="post-time">${new Date(post.created_at).toLocaleString()}</div>
                </div>
            </div>
            <div class="post-content">${escapeHtml(post.content)}</div>
            ${imageHtml}
            <div class="post-actions">
                <button onclick="toggleLike(${post.id})" class="post-action-btn ${likedClass}">
                    ❤️ <span id="like-count-${post.id}">${post.like_count}</span>
                </button>
                <button onclick="toggleComments(${post.id})" class="post-action-btn">
                    💬 <span id="comment-count-${post.id}">${post.comment_count}</span>
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
        if (likeCountSpan) likeCountSpan.textContent = data.like_count;
        const btn = document.querySelector(`.post[data-post-id="${postId}"] .post-action-btn.liked, .post[data-post-id="${postId}"] .post-action-btn:first-child`);
        if (btn) {
            if (data.action === 'liked') btn.classList.add('liked');
            else btn.classList.remove('liked');
        }
    } catch (e) { alert(e.message); }
}

async function toggleComments(postId) {
    const commentsDiv = document.getElementById(`comments-${postId}`);
    if (!commentsDiv) return;
    if (commentsDiv.style.display === 'none') {
        try {
            const comments = await apiCall('GET', `/api/social/posts/${postId}/comments`);
            let html = '<h4>Комментарии</h4>';
            comments.forEach(c => {
                html += `
                    <div class="comment">
                        <img src="${c.author_avatar || '/static/default_avatar.png'}" class="comment-avatar" onerror="this.src='/static/default_avatar.png'">
                        <div class="comment-content">
                            <div class="comment-author">${escapeHtml(c.author_nickname || 'Аноним')}</div>
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
        } catch (e) { alert(e.message); }
    } else {
        commentsDiv.style.display = 'none';
    }
}

async function addComment(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    if (!input) return;
    const content = input.value.trim();
    if (!content) return;
    try {
        await apiCall('POST', `/api/social/posts/${postId}/comments`, { content });
        input.value = '';
        toggleComments(postId);
        const countSpan = document.getElementById(`comment-count-${postId}`);
        if (countSpan) countSpan.textContent = parseInt(countSpan.textContent) + 1;
    } catch (e) { alert(e.message); }
}