/* Hero: correlated GBM paths fanning out in real time, worst 5% tinted red,
   the VaR level drawn as a dashed line. Pure canvas, no dependencies. */
(() => {
  const canvas = document.getElementById("hero-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const N = 180, STEPS = 120;
  let W, H, dpr, paths, finals, varLevel, t0, scale = 1;

  const randn = () => {
    let u = 0, v = 0;
    while (!u) u = Math.random();
    while (!v) v = Math.random();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };

  function simulate() {
    const mu = 0.0004, sig = 0.012, common = 0.55;
    paths = [];
    const market = Array.from({ length: STEPS }, randn);
    for (let i = 0; i < N; i++) {
      const p = new Float32Array(STEPS + 1);
      p[0] = 0;
      for (let s = 1; s <= STEPS; s++) {
        const z = common * market[s - 1] * 0.35 + Math.sqrt(1 - common * common * 0.35 * 0.35) * randn();
        p[s] = p[s - 1] + mu - 0.5 * sig * sig + sig * z;
      }
      paths.push(p);
    }
    finals = paths.map((p) => p[STEPS]).sort((a, b) => a - b);
    varLevel = finals[Math.floor(N * 0.05)];
    scale = 1 / Math.max(Math.abs(finals[2]), Math.abs(finals[N - 3]));
    t0 = performance.now();
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  const x0 = () => W * (W < 720 ? 0.05 : 0.38);
  const yOf = (v) => (W < 720 ? H * 0.24 - v * scale * H * 0.12 : H * 0.42 - v * scale * H * 0.3);
  const xOf = (s) => x0() + (s / STEPS) * (W * 0.98 - x0());

  function draw(progress) {
    ctx.clearRect(0, 0, W, H);
    const upto = Math.max(1, Math.floor(progress * STEPS));

    // grid
    ctx.strokeStyle = "rgba(255,255,255,0.04)";
    ctx.lineWidth = 1;
    for (let gx = 0; gx <= 10; gx++) {
      const x = x0() + (gx / 10) * (W * 0.98 - x0());
      ctx.beginPath(); ctx.moveTo(x, H * 0.08); ctx.lineTo(x, H * 0.92); ctx.stroke();
    }

    for (const p of paths) {
      const tail = p[STEPS] <= varLevel;
      ctx.strokeStyle = tail ? "rgba(255,107,107,0.55)" : "rgba(197,168,255,0.13)";
      ctx.lineWidth = tail ? 1.2 : 1;
      ctx.beginPath();
      ctx.moveTo(xOf(0), yOf(p[0]));
      for (let s = 1; s <= upto; s++) ctx.lineTo(xOf(s), yOf(p[s]));
      ctx.stroke();
    }

    // origin
    ctx.fillStyle = "#ecebe6";
    ctx.beginPath(); ctx.arc(xOf(0), yOf(0), 3, 0, Math.PI * 2); ctx.fill();

    if (progress >= 1) {
      const y = yOf(varLevel);
      ctx.setLineDash([4, 6]);
      ctx.strokeStyle = "rgba(255,107,107,0.8)";
      ctx.beginPath(); ctx.moveTo(x0(), y); ctx.lineTo(W * 0.98, y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "#ff6b6b";
      ctx.font = "11px JetBrains Mono, monospace";
      ctx.textAlign = "right";
      ctx.fillText(`VaR 95%  ${(-(Math.exp(varLevel) - 1) * 100).toFixed(1)}%`, W * 0.98, y - 8);
    }
    const legend = document.getElementById("hero-paths");
    if (legend) legend.textContent = `${N} paths · day ${upto}/${STEPS}`;
  }

  const DURATION = 5200, HOLD = 2600;
  function frame(now) {
    const el = now - t0;
    if (el > DURATION + HOLD) simulate();
    draw(Math.min(1, (now - t0) / DURATION));
    if (visible) requestAnimationFrame(frame);
  }

  let visible = true;
  resize();
  simulate();
  window.addEventListener("resize", () => { resize(); if (Q.reduceMotion) draw(1); });

  if (Q.reduceMotion) { draw(1); return; }
  new IntersectionObserver(([e]) => {
    const was = visible;
    visible = e.isIntersecting;
    if (visible && !was) requestAnimationFrame(frame);
  }).observe(canvas);
  requestAnimationFrame(frame);
})();
