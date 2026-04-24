document.addEventListener('change', function(e) {
    if (e.target.id === 'postImage') {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(ev) {
                document.getElementById('imagePreview').innerHTML = '<img src="' + ev.target.result + '" alt="Preview">';
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
    if (imageInput.files[0]) formData.append('image', imageInput.files[0]);
    const res = await fetch('/api/social/posts', { method: 'POST', body: formData });
    if (res.ok) {
        document.getElementById('postContent').value = '';
        imageInput.value = '';
        document.getElementById('imagePreview').innerHTML = '';
        loadFeed();
    }
}

async function loadFeed() {
    if (!currentUser?.player) return;
    try {
        const res = await fetch('/api/social/posts/feed');
        const posts = await res.json();
        renderPosts(posts, 'feedContainer');
    } catch (e) {}
}

function renderPosts(posts, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!posts.length) { container.innerHTML = '<p>Пока нет постов.</p>'; return; }
    container.innerHTML = posts.map(post => {
        const avatar = post.author_avatar || '/static/default_avatar.png';
        const liked = post.liked_by_me ? 'liked' : '';
        const img = post.image_url ? '<img src="' + post.image_url + '" class="post-image">' : '';
        return '<div class="post" data-post-id="' + post.id + '">' +
            '<div class="post-header"><img src="' + avatar + '" class="post-avatar" onerror="this.src=\'/static/default_avatar.png\'">' +
            '<div class="post-author-info"><div class="post-author-name">' + escapeHtml(post.author_discord_username) + '</div>' +
            '<div class="post-author-nick">@' + escapeHtml(post.author_nickname) + '</div>' +
            '<div class="post-time">' + new Date(post.created_at).toLocaleString() + '</div></div></div>' +
            '<div class="post-content">' + escapeHtml(post.content) + '</div>' + img +
            '<div class="post-actions">' +
            '<button onclick="toggleLike(' + post.id + ')" class="post-action-btn ' + liked + '">❤️ <span id="like-count-' + post.id + '">' + post.like_count + '</span></button>' +
            '<button onclick="toggleComments(' + post.id + ')" class="post-action-btn">💬 <span id="comment-count-' + post.id + '">' + post.comment_count + '</span></button>' +
            '</div><div id="comments-' + post.id + '" class="comments-section" style="display:none;"></div></div>';
    }).join('');
}

async function toggleLike(postId) {
    const res = await fetch('/api/social/posts/' + postId + '/like', { method: 'POST' });
    const data = await res.json();
    document.getElementById('like-count-' + postId).textContent = data.like_count;
    const btn = document.querySelector('.post[data-post-id="' + postId + '"] .post-action-btn');
    if (btn) btn.classList.toggle('liked', data.action === 'liked');
}

async function toggleComments(postId) {
    const div = document.getElementById('comments-' + postId);
    if (div.style.display === 'none') {
        const res = await fetch('/api/social/posts/' + postId + '/comments');
        const comments = await res.json();
        let html = '<h4>Комментарии</h4>';
        comments.forEach(c => {
            html += '<div class="comment"><img src="' + (c.author_avatar || '/static/default_avatar.png') + '" class="comment-avatar">' +
                '<div class="comment-content"><div class="comment-author">' + escapeHtml(c.author_nickname) + '</div>' +
                '<div class="comment-text">' + escapeHtml(c.content) + '</div></div></div>';
        });
        html += '<textarea id="comment-input-' + postId + '" placeholder="Комментарий..."></textarea>' +
            '<button onclick="addComment(' + postId + ')">Отправить</button>';
        div.innerHTML = html;
        div.style.display = 'block';
    } else {
        div.style.display = 'none';
    }
}

async function addComment(postId) {
    const input = document.getElementById('comment-input-' + postId);
    if (!input) return;
    const content = input.value.trim();
    if (!content) return;
    await fetch('/api/social/posts/' + postId + '/comments', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ content })
    });
    input.value = '';
    toggleComments(postId);
    const span = document.getElementById('comment-count-' + postId);
    if (span) span.textContent = parseInt(span.textContent) + 1;
}ы