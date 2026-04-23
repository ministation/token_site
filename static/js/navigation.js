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
                document.getElementById('socialSearchInput').value = '';
                document.getElementById('searchResults').innerHTML = '';
            } else if (section === 'messages') {
                loadDialogs();
            }
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(sectionId + 'Section');
    if (target) target.classList.add('active');
}