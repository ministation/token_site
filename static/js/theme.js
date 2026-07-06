// Переключение темы: светлая по умолчанию, тёмная «космическая».
// Подключается в <head>, чтобы тема применялась до отрисовки страницы.
(function () {
    const saved = localStorage.getItem('ms-theme');
    document.documentElement.dataset.theme = saved === 'dark' ? 'dark' : 'light';
})();

function updateThemeToggle() {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    const dark = document.documentElement.dataset.theme === 'dark';
    btn.innerHTML = dark ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
    btn.title = dark ? 'Светлая тема' : 'Тёмная тема';
    btn.setAttribute('aria-label', btn.title);
}

function toggleTheme() {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('ms-theme', root.dataset.theme);
    updateThemeToggle();
    // Графики перерисовываются под цвета новой темы
    window.dispatchEvent(new Event('themechange'));
}

document.addEventListener('DOMContentLoaded', updateThemeToggle);
