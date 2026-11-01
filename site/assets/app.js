/* Shared helpers: data loading (live API -> static snapshot fallback),
   number formatting, Plotly theme, nav + scroll reveal. */
(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Nav & reveal ----------
  const nav = document.querySelector(".nav");
  const onScroll = () => nav && nav.classList.toggle("scrolled", window.scrollY > 20);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

  document.querySelectorAll(".project").forEach((card) => {
    card.addEventListener("pointermove", (e) => {
      const r = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${e.clientX - r.left}px`);
      card.style.setProperty("--my", `${e.clientY - r.top}px`);
    });
  });

  // ---------- Formatting ----------
  const isNum = (v) => typeof v === "number" && isFinite(v);
  const fmt = {
    pct: (v, d = 2) => (isNum(v) ? `${(v * 100).toFixed(d)}%` : "—"),
    spct: (v, d = 2) => (isNum(v) ? `${v >= 0 ? "+" : ""}${(v * 100).toFixed(d)}%` : "—"),
    num: (v, d = 2) => (isNum(v) ? v.toFixed(d) : "—"),
    money: (v) => (isNum(v) ? v.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }) : "—"),
    sign: (v) => (isNum(v) ? (v >= 0 ? "up" : "down") : ""),
  };

  // ---------- Data loading ----------
  let liveApi = null;
  async function hasApi() {
    if (liveApi !== null) return liveApi;
    if (location.protocol === "file:" || location.hostname.endsWith("github.io")) return (liveApi = false);
    try {
      const ctl = new AbortController();
      setTimeout(() => ctl.abort(), 2500);
      const r = await fetch("/api/health", { signal: ctl.signal });
      liveApi = r.ok && (await r.json()).ok === true;
    } catch { liveApi = false; }
    document.body.classList.toggle("live", liveApi);
    return liveApi;
  }

  // Tickers pre-computed daily by build_static.py (GitHub Actions)
  let universeP = null;
  const universe = () => (universeP ||= fetch("data/universe.json").then((r) => (r.ok ? r.json() : null)).catch(() => null));
  const snapName = (...t) => t.map((x) => x.toUpperCase().replace("^", "-")).join("_"); // matches build_static.fname
  async function fillList(id, key) {
    const u = await universe();
    const el = document.getElementById(id);
    if (u && el) el.innerHTML = u[key].map((t) => `<option value="${t}">`).join("");
  }

  /* Returns { data, mode }: "live" when app.py runs locally, else the daily
     pre-computed file. `snapshot` is null when the inputs were not pre-computed. */
  async function load(apiPath, snapshot) {
    if (await hasApi()) {
      const r = await fetch(apiPath);
      const body = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(body.error || `Request failed (${r.status})`);
      return { data: body, mode: "live" };
    }
    const r = snapshot ? await fetch(`data/${snapshot}.json`) : null;
    if (!r || !r.ok) throw new Error("Not in the list. Pick a ticker from the suggestions.");
    return { data: await r.json(), mode: "snapshot" };
  }

  function setMode(el, mode, extra = "") {
    if (!el) return;
    el.className = `mode ${mode}`;
    el.innerHTML = `<span class="dot"></span>${mode === "live" ? "Live data" : "Updated daily"} ${extra}`;
  }

  // ---------- Plotly theme ----------
  const css = getComputedStyle(document.documentElement);
  const c = (n) => css.getPropertyValue(n).trim();
  const colors = {
    ink: c("--ink"), ink2: c("--ink-2"), ink3: c("--ink-3"), line: c("--line"),
    accent: c("--accent"), accent2: c("--accent-2"), up: c("--up"), down: c("--down"), warn: c("--warn"),
  };
  const baseLayout = (extra = {}) => ({
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "JetBrains Mono, monospace", size: 11, color: colors.ink2 },
    margin: { l: 52, r: 16, t: 40, b: 40 },
    hovermode: "x unified",
    hoverlabel: { bgcolor: "#16181d", bordercolor: colors.line, font: { color: colors.ink, family: "JetBrains Mono" } },
    legend: { orientation: "h", y: 1.1, x: 0, font: { size: 11 }, bgcolor: "rgba(0,0,0,0)" },
    xaxis: { gridcolor: colors.line, zeroline: false, linecolor: colors.line, ...extra.xaxis },
    yaxis: { gridcolor: colors.line, zeroline: false, linecolor: colors.line, ...extra.yaxis },
    ...Object.fromEntries(Object.entries(extra).filter(([k]) => !["xaxis", "yaxis"].includes(k))),
  });
  const plotConfig = { displayModeBar: false, responsive: true };
  const plot = (id, traces, layout) => Plotly.react(id, traces, baseLayout(layout), plotConfig);

  window.Q = { fmt, load, setMode, colors, plot, baseLayout, reduceMotion, hasApi, universe, snapName, fillList };
})();
