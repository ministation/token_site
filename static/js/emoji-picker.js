const EMOJI_SET = [
    '😀', '😂', '🥹', '😍', '🤔', '😎', '🥳', '😭', '😡', '👍',
    '👎', '❤️', '🔥', '⭐', '✨', '🎉', '💀', '👀', '🙏', '💪',
    '🚀', '🎮', '🛸', '👽', '🤖', '💬', '📢', '🎵', '🍕', '☕',
    '⚡', '✅', '❌', '❓', '‼️', '🫡', '🤝', '👋', '🐱', '🐶',
];

function setEmojiPickerOpen(picker, open) {
    if (!picker) return;
    picker.classList.toggle('is-open', open);
    picker.hidden = !open;
}

function setupEmojiPicker(inputId, btnId, pickerId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    const picker = document.getElementById(pickerId);
    if (!input || !btn || !picker || picker.dataset.bound) return;
    picker.dataset.bound = '1';

    setEmojiPickerOpen(picker, false);
    picker.innerHTML = EMOJI_SET.map(e =>
        `<button type="button" class="emoji-pick-btn" data-emoji="${e}">${e}</button>`
    ).join('');

    btn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        setEmojiPickerOpen(picker, !picker.classList.contains('is-open'));
    });

    picker.addEventListener('click', (ev) => {
        const pick = ev.target.closest('.emoji-pick-btn');
        if (!pick) return;
        const emoji = pick.dataset.emoji || '';
        const start = input.selectionStart ?? input.value.length;
        const end = input.selectionEnd ?? input.value.length;
        input.value = input.value.slice(0, start) + emoji + input.value.slice(end);
        input.focus();
        input.selectionStart = input.selectionEnd = start + emoji.length;
        setEmojiPickerOpen(picker, false);
    });

    document.addEventListener('click', (ev) => {
        if (!picker.classList.contains('is-open')) return;
        if (!ev.target.closest(`#${pickerId}`) && !ev.target.closest(`#${btnId}`)) {
            setEmojiPickerOpen(picker, false);
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupEmojiPicker('globalChatInput', 'globalChatEmojiBtn', 'globalChatEmojiPicker');
    setupEmojiPicker('pmInput', 'pmEmojiBtn', 'pmEmojiPicker');
});
