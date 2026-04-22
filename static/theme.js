(function() {
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    updateToggleIcon(savedTheme);
    
    themeToggle.addEventListener('click', () => {
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateToggleIcon(newTheme);
    });
    
    function updateToggleIcon(theme) {
        themeToggle.textContent = theme === 'light' ? '🌙' : '☀️';
    }
})();