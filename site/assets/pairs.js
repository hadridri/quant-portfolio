(() => {
  const { fmt, load, setMode, colors: C, plot, universe, snapName, hasApi, fillList } = Q;
  const $ = (id) => document.getElementById(id);
  fillList("pair-list", "pairs");
  const DEFAULTS = { period: "5y", window: "30", entry: "2", exit: "0.5", stop: "3.5", cost: "5", hedge_window: "120", rolling: "1" };

  document.querySelectorAll(".presets button").forEach((b) => b.addEventListener("click", () => {
    [$("a").value, $("b").value] = b.dataset.p.split(","); run();
  }));
  $("form").addEventListener("submit", (e) => { e.preventDefault(); run(); });

  // Allow deep links: pairs.html?a=XOM&b=CVX
  const qs = new URLSearchParams(location.search);
  if (qs.get("a") && qs.get("b")) { $("a").value = qs.get("a"); $("b").value = qs.get("b"); }

  async function run() {
    let a = $("a").value.trim().toUpperCase(), b = $("b").value.trim().toUpperCase();
    // Daily results are computed once per pair, in alphabetical order
    if (!(await hasApi()) && a > b) { [a, b] = [b, a]; $("a").value = a; $("b").value = b; }
    const q = new URLSearchParams({
      a, b, period: $("period").value, window: $("window").value, entry: $("entry").value, exit: $("exit").value,
      stop: $("stop").value, cost: $("cost").value, hedge_window: $("hedge").value, rolling: $("rolling").value,
    });
    const isDefault = Object.entries(DEFAULTS).every(([k, v]) => parseFloat(q.get(k)) === parseFloat(v) || q.get(k) === v);
    const u = await universe();
    const snap = isDefault && u && a !== b && u.pairs.includes(a) && u.pairs.includes(b) ? `pairs_${snapName(a, b)}` : null;

    $("results").classList.add("loading"); $("run").disabled = true; $("error").classList.remove("show");
    try {
      const { data, mode } = await load(`/api/pairs?${q}`, snap);
      setMode($("mode"), mode, `· ${data.params.end}`);
      history.replaceState(null, "", `?a=${a}&b=${b}`);
      render(data);
    } catch (err) {
      $("error").textContent = err.message; $("error").classList.add("show");
    } finally {
      $("results").classList.remove("loading"); $("run").disabled = false;
    }
  }

  function render(d) {
    const t = d.tests, s = d.stats, p = d.params, S = d.series;
    const vClass = { Tradeable: "good", Caution: "mid" }[d.verdict.label] || "bad";
    $("verdict").className = `verdict ${vClass}`;
    $("v-badge").textContent = d.verdict.label;
    $("v-text").textContent = `${p.a} / ${p.b}: ${d.verdict.text}`;

    $("t-p").textContent = fmt.num(t.coint_p, 3); $("t-p").className = `value ${t.coint_p < 0.05 ? "up" : "down"}`;
    $("t-adf").textContent = `ADF on spread ${fmt.num(t.adf_p, 3)}`;
    const hlOk = t.half_life >= 5 && t.half_life <= 30;
    $("t-hl").textContent = t.half_life === null ? "∞" : `${fmt.num(t.half_life, 1)}d`;
    $("t-hl").className = `value ${hlOk ? "up" : "warn"}`;
    $("t-beta").textContent = fmt.num(t.beta, 3); $("t-r2").textContent = `R² ${fmt.num(t.r2)} · latest ${fmt.num(t.beta_latest)}`;
    $("t-z").textContent = fmt.num(t.z_latest); $("t-z").className = `value ${Math.abs(t.z_latest) > p.entry ? "warn" : ""}`;
    $("t-pos").textContent = ["Short spread", "Flat", "Long spread"][t.position_latest + 1];
    $("t-sh").textContent = fmt.num(s.sharpe); $("t-sh").className = `value ${fmt.sign(s.sharpe)}`;
    $("t-cagr").textContent = `CAGR ${fmt.spct(s.cagr)}`;
    $("t-dd").textContent = fmt.pct(s.max_drawdown, 1); $("t-vol").textContent = `vol ${fmt.pct(s.volatility, 1)}`;
    $("t-n").textContent = s.n_trades; $("t-win").textContent = s.win_rate === null ? "—" : `win rate ${fmt.pct(s.win_rate, 0)}`;
    $("t-tim").textContent = fmt.pct(s.time_in_market, 0); $("t-cost").textContent = `costs ${fmt.pct(s.total_costs)}`;

    const x = S.dates, h = (y, color, dash) => ({ type: "line", xref: "paper", x0: 0, x1: 1, y0: y, y1: y, line: { color, width: 1, dash } });
    const ev = (k, sym, color, name) => ({
      x: d.events[k].dates, y: d.events[k].z, mode: "markers", name,
      marker: { symbol: sym, size: 10, color, line: { width: 1, color: "#000" } }, hovertemplate: `${name} z=%{y:.2f}<extra></extra>`,
    });
    plot("c-z", [
      { x, y: S.z, name: "z-score", line: { color: C.accent2, width: 1.2 }, hovertemplate: "%{y:.2f}" },
      ev("long", "triangle-up", C.up, "Long spread"), ev("short", "triangle-down", C.down, "Short spread"),
      ev("exit", "circle", C.ink, "Exit"), ev("stop", "x", C.warn, "Stop-loss"),
    ], {
      shapes: [h(p.entry, C.down, "dash"), h(-p.entry, C.up, "dash"), h(p.exit, C.ink3, "dot"), h(-p.exit, C.ink3, "dot"),
               h(p.stop, C.warn, "dot"), h(-p.stop, C.warn, "dot"), h(0, C.line)],
      yaxis: { range: [-Math.max(5, p.stop + 1), Math.max(5, p.stop + 1)] },
    });

    plot("c-px", [
      { x, y: S.a100, name: p.a, line: { color: C.accent2, width: 1.5 } },
      { x, y: S.b100, name: p.b, line: { color: C.up, width: 1.5 } },
    ]);
    plot("c-eq", [{ x, y: S.equity, name: "Strategy", fill: "tozeroy", fillcolor: "rgba(155,107,255,0.08)", line: { color: C.accent2, width: 2 }, hovertemplate: "%{y:.3f}" }],
      { showlegend: false, yaxis: { title: { text: "Growth of $1" } } });
    plot("c-roll", [{ x: d.rolling_coint.dates, y: d.rolling_coint.p, mode: "lines+markers", name: "p-value",
      line: { color: C.accent2, width: 1.5 }, marker: { size: 4, color: d.rolling_coint.p.map((v) => (v < 0.05 ? C.up : C.down)) }, hovertemplate: "%{y:.3f}" }],
      { showlegend: false, shapes: [h(0.05, C.up, "dash")], yaxis: { range: [0, 1] } });
    plot("c-beta", [{ x, y: S.beta, name: "β", line: { color: C.warn, width: 1.5 }, hovertemplate: "%{y:.3f}" }],
      { showlegend: false, shapes: [h(t.beta, C.ink3, "dot")] });

    $("trades").innerHTML = `<tr><th>Entry</th><th>Exit</th><th>Side</th><th>Days</th><th>P&amp;L</th></tr>` + (d.trades.length
      ? d.trades.slice().reverse().map((r) => `<tr><td>${r.entry}</td><td>${r.exit}</td><td>${r.side}</td><td>${r.days}</td><td class="${fmt.sign(r.pnl)}">${fmt.spct(r.pnl)}</td></tr>`).join("")
      : `<tr><td colspan="5">No completed trades with these thresholds.</td></tr>`);
  }

  run();
})();
