(function () {
    const ambient = document.querySelector('.bg-ambient');
    if (!ambient || ambient.dataset.ambientReady === '1') return;
    ambient.dataset.ambientReady = '1';

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let dustField = ambient.querySelector('.bg-dust-field');
    if (!dustField) {
        dustField = document.createElement('div');
        dustField.className = 'bg-parallax-layer bg-dust-field';
        dustField.dataset.depth = '34';
        ambient.appendChild(dustField);
    }

    let starsFar = ambient.querySelector('.bg-stars-far');
    if (!starsFar) {
        starsFar = document.createElement('div');
        starsFar.className = 'bg-parallax-layer bg-stars-far';
        starsFar.dataset.depth = '12';
        ambient.insertBefore(starsFar, dustField);
    }
    let starsNear = ambient.querySelector('.bg-stars-near');
    if (!starsNear) {
        starsNear = document.createElement('div');
        starsNear.className = 'bg-parallax-layer bg-stars-near';
        starsNear.dataset.depth = '48';
        ambient.appendChild(starsNear);
    }

    // Avoid stacking particles if script reloads
    for (const layer of [starsFar, dustField, starsNear]) {
        layer.querySelectorAll('.dust-particle').forEach((el) => el.remove());
    }

    const parallaxLayers = [...ambient.querySelectorAll('.bg-parallax-layer')];
    const isMobile = window.innerWidth < 768;
    const COUNTS = {
        far: isMobile ? 12 : 22,
        mid: isMobile ? 10 : 16,
        near: isMobile ? 5 : 8,
    };

    const COLORS = [
        'rgba(255, 220, 120, 0.7)',
        'rgba(255, 200, 46, 0.55)',
        'rgba(255, 170, 40, 0.45)',
        'rgba(255, 255, 240, 0.75)',
        'rgba(240, 140, 30, 0.4)',
    ];

    function rand(min, max) {
        return min + Math.random() * (max - min);
    }

    function spawn(container, className, count, sizeRange, driftScale) {
        if (!container || reducedMotion) return;
        for (let i = 0; i < count; i++) {
            const p = document.createElement('span');
            p.className = className;
            const size = rand(sizeRange[0], sizeRange[1]);
            p.style.width = `${size}px`;
            p.style.height = `${size}px`;
            p.style.left = `${rand(0, 100)}%`;
            p.style.top = `${rand(0, 100)}%`;
            p.style.background = COLORS[Math.floor(Math.random() * COLORS.length)];
            // Set animation params once — changing them later restarts CSS animations
            // and causes the “accelerating blink” effect over time.
            p.style.setProperty('--op', rand(0.18, 0.55).toFixed(2));
            p.style.setProperty('--tx', `${rand(-140, 140) * driftScale}px`);
            p.style.setProperty('--ty', `${rand(-120, 120) * driftScale}px`);
            p.style.setProperty('--dur', `${rand(42, 78)}s`);
            p.style.setProperty('--delay', `${-rand(0, 60)}s`);
            p.style.setProperty('--twinkle', `${rand(10, 22)}s`);
            p.style.setProperty('--twinkle-delay', `${-rand(0, 18)}s`);
            container.appendChild(p);
        }
    }

    if (!reducedMotion) {
        spawn(starsFar, 'dust-particle dust-particle--far', COUNTS.far, [1.5, 3], 0.45);
        spawn(dustField, 'dust-particle dust-particle--mid', COUNTS.mid, [2.5, 5.5], 0.85);
        spawn(starsNear, 'dust-particle dust-particle--near', COUNTS.near, [4, 8], 1.1);
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
        currentX += (targetX - currentX) * 0.06;
        currentY += (targetY - currentY) * 0.06;

        for (const layer of parallaxLayers) {
            const depth = Number(layer.dataset.depth) || 24;
            layer.style.transform = `translate3d(${currentX * depth * 0.55}px, ${currentY * depth * 0.45}px, 0)`;
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
