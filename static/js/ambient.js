(function () {
    const ambient = document.querySelector('.bg-ambient');
    if (!ambient) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let dustField = ambient.querySelector('.bg-dust-field');
    if (!dustField) {
        dustField = document.createElement('div');
        dustField.className = 'bg-parallax-layer bg-dust-field';
        dustField.dataset.depth = '34';
        ambient.appendChild(dustField);
    }

    // Extra depth layers for parallax (near stars / mid dust)
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

    const parallaxLayers = [...ambient.querySelectorAll('.bg-parallax-layer')];
    const isMobile = window.innerWidth < 768;
    const COUNTS = {
        far: isMobile ? 18 : 36,
        mid: isMobile ? 14 : 28,
        near: isMobile ? 8 : 14,
    };

    const COLORS = [
        'rgba(255, 220, 120, 0.85)',
        'rgba(255, 200, 46, 0.7)',
        'rgba(255, 170, 40, 0.55)',
        'rgba(255, 255, 240, 0.9)',
        'rgba(240, 140, 30, 0.5)',
    ];

    function rand(min, max) {
        return min + Math.random() * (max - min);
    }

    function spawn(container, className, count, sizeRange, driftScale) {
        if (!container || reducedMotion) return;
        for (let i = 0; i < count; i++) {
            const p = document.createElement('span');
            p.className = className;
            resetParticle(p, sizeRange, driftScale);
            p.addEventListener('animationiteration', () => resetParticle(p, sizeRange, driftScale));
            container.appendChild(p);
        }
    }

    function resetParticle(el, sizeRange, driftScale) {
        const size = rand(sizeRange[0], sizeRange[1]);
        el.style.width = `${size}px`;
        el.style.height = `${size}px`;
        el.style.left = `${rand(0, 100)}%`;
        el.style.top = `${rand(0, 100)}%`;
        el.style.background = COLORS[Math.floor(Math.random() * COLORS.length)];
        el.style.setProperty('--op', rand(0.2, 0.75).toFixed(2));
        el.style.setProperty('--tx', `${rand(-180, 180) * driftScale}px`);
        el.style.setProperty('--ty', `${rand(-160, 160) * driftScale}px`);
        el.style.setProperty('--dur', `${rand(18, 48)}s`);
        el.style.setProperty('--delay', `${rand(0, 20)}s`);
        el.style.setProperty('--twinkle', `${rand(2.5, 6.5)}s`);
    }

    if (!reducedMotion) {
        spawn(starsFar, 'dust-particle dust-particle--far', COUNTS.far, [1.5, 3.5], 0.55);
        spawn(dustField, 'dust-particle dust-particle--mid', COUNTS.mid, [3, 7], 1);
        spawn(starsNear, 'dust-particle dust-particle--near', COUNTS.near, [5, 11], 1.35);
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
            // Small delta (skill: keep parallax subtle, 5–15 feel)
            layer.style.transform = `translate3d(${currentX * depth}px, ${currentY * depth * 0.85}px, 0)`;
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
