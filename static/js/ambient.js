(function () {
    const ambient = document.querySelector('.bg-ambient');
    if (!ambient) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dustField = ambient.querySelector('.bg-dust-field');
    const parallaxLayers = [...ambient.querySelectorAll('.bg-parallax-layer')];

    const PARTICLE_COUNT = window.innerWidth < 768 ? 12 : 20;
    const COLORS = [
        'rgba(255, 200, 46, 0.55)',
        'rgba(255, 200, 46, 0.38)',
        'rgba(240, 120, 10, 0.48)',
        'rgba(240, 120, 10, 0.32)',
    ];

    function rand(min, max) {
        return min + Math.random() * (max - min);
    }

    function resetParticle(el) {
        const size = rand(6, 12);
        el.style.width = `${size}px`;
        el.style.height = `${size}px`;
        el.style.left = `${rand(0, 100)}%`;
        el.style.top = `${rand(0, 100)}%`;
        el.style.background = COLORS[Math.floor(Math.random() * COLORS.length)];
        el.style.setProperty('--op', rand(0.25, 0.65).toFixed(2));
        el.style.setProperty('--tx', `${rand(-140, 140)}px`);
        el.style.setProperty('--ty', `${rand(-120, 120)}px`);
        el.style.setProperty('--dur', `${rand(22, 52)}s`);
        el.style.setProperty('--delay', `${rand(0, 18)}s`);
    }

    if (dustField && !reducedMotion) {
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const p = document.createElement('span');
            p.className = 'dust-particle';
            resetParticle(p);
            p.addEventListener('animationiteration', () => resetParticle(p));
            dustField.appendChild(p);
        }
    }

    if (reducedMotion || !parallaxLayers.length) return;

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
        currentX += (targetX - currentX) * 0.08;
        currentY += (targetY - currentY) * 0.08;

        for (const layer of parallaxLayers) {
            const depth = Number(layer.dataset.depth) || 24;
            layer.style.transform = `translate3d(${currentX * depth}px, ${currentY * depth}px, 0)`;
        }

        const settled = Math.abs(targetX - currentX) < 0.002 && Math.abs(targetY - currentY) < 0.002;
        rafId = settled ? null : requestAnimationFrame(tick);
    }

    window.addEventListener('mousemove', (e) => setTarget(e.clientX, e.clientY), { passive: true });
    window.addEventListener('touchmove', (e) => {
        const touch = e.touches[0];
        if (touch) setTarget(touch.clientX, touch.clientY);
    }, { passive: true });
})();
