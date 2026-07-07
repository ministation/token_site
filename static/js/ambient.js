(function () {
    const ambient = document.querySelector('.bg-ambient');
    if (!ambient) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const layers = [...ambient.querySelectorAll('.bg-parallax-layer')];
    if (!layers.length) return;

    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;
    let rafId = null;

    function setTarget(clientX, clientY) {
        targetX = (clientX / window.innerWidth - 0.5) * 2;
        targetY = (clientY / window.innerHeight - 0.5) * 2;
        if (!rafId) rafId = requestAnimationFrame(tick);
    }

    function tick() {
        currentX += (targetX - currentX) * 0.1;
        currentY += (targetY - currentY) * 0.1;

        for (const layer of layers) {
            const depth = Number(layer.dataset.depth) || 30;
            layer.style.transform = `translate3d(${currentX * depth}px, ${currentY * depth}px, 0)`;
        }

        const settled = Math.abs(targetX - currentX) < 0.002 && Math.abs(targetY - currentY) < 0.002;
        if (!settled) {
            rafId = requestAnimationFrame(tick);
        } else {
            rafId = null;
        }
    }

    window.addEventListener('mousemove', (e) => setTarget(e.clientX, e.clientY), { passive: true });
    window.addEventListener('touchmove', (e) => {
        const touch = e.touches[0];
        if (touch) setTarget(touch.clientX, touch.clientY);
    }, { passive: true });
})();
