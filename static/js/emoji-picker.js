const EMOJI_SET = [
    '😀', '😂', '🥹', '😍', '🤔', '😎', '🥳', '😭', '😡', '👍',
    '👎', '❤️', '🔥', '⭐', '✨', '🎉', '💀', '👀', '🙏', '💪',
    '🚀', '🎮', '🛸', '👽', '🤖', '💬', '📢', '🎵', '🍕', '☕',
    '⚡', '✅', '❌', '❓', '‼️', '🫡', '🤝', '👋', '🐱', '🐶',
];

function setupEmojiPicker(inputId, btnId, pickerId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    const picker = document.getElementById(pickerId);
    if (!input || !btn || !picker || picker.dataset.bound) return;
    picker.dataset.bound = '1';

    picker.innerHTML = EMOJI_SET.map(e =>
        `<button type="button" class="emoji-pick-btn" data-emoji="${e}">${e}</button>`
    ).join('');

    btn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        picker.hidden = !picker.hidden;
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
        picker.hidden = true;
    });

    document.addEventListener('click', (ev) => {
        if (!picker.hidden && !ev.target.closest(`#${pickerId}`) && ev.target !== btn) {
            picker.hidden = true;
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupEmojiPicker('globalChatInput', 'globalChatEmojiBtn', 'globalChatEmojiPicker');
    setupEmojiPicker('pmInput', 'pmEmojiBtn', 'pmEmojiPicker');
});
