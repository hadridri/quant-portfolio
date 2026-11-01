(() => {
  const { fmt, load, setMode, colors: C, plot, universe, snapName, fillList } = Q;
  const $ = (id) => document.getElementById(id);
  fillList("sma-list", "sma");

  document.querySelectorAll(".presets button").forEach((b) => b.addEventListener("click", () => { $("ticker").value = b.dataset.t; run(); }));
  $("form").addEventListener("submit", (e) => { e.preventDefault(); run(); });

  async function run() {
    const ticker = $("ticker").value.trim().toUpperCase();
    const q = new URLSearchParams({ ticker, fast: $("fast").value, slow: $("slow").value, years: $("years").value, cost: $("cost").value, execution: $("execution").value });
    const isDefault = q.get("fast") === "50" && q.get("slow") === "200" && q.get("years") === "20" && q.get("cost") === "10" && q.get("execution") === "next_open";
    const u = await universe();
    const snap = isDefault && u && u.sma.includes(ticker) ? `sma_${snapName(ticker)}` : null;

    $("results").classList.add("loading"); $("run").disabled = true; $("error").classList.remove("show");
    try {
      const { data, mode } = await load(`/api/sma?${q}`, snap);
      setMode($("mode"), mode, `· ${data.params.end}`);
      render(data);
    } catch (err) {
      $("error").textContent = err.message; $("error").classList.add("show");
    } finally {
      $("results").classList.remove("loading"); $("run").disabled = false;
    }
  }

  function render(d) {
    const st = d.status, s = d.strategy, b = d.buy_hold, p = d.params, S = d.series;
    const bull = st.regime === "bullish";
    $("status").style.color = bull ? C.up : C.down;
    $("s-eyebrow").textContent = `${p.ticker} · as of ${st.as_of}`;
    $("s-regime").textContent = bull ? `Golden cross: SMA ${p.fast} above ${p.slow}` : `Death cross: SMA ${p.fast} below ${p.slow}`;
    $("s-detail").textContent = st.last_cross
      ? `Last ${st.last_cross.type} cross on ${st.last_cross.date} (${st.days_since_cross} sessions ago). Gap between averages: ${fmt.spct(st.gap)}.`
      : "No cross in the selected window.";
    $("s-levels").innerHTML = `Close ${fmt.num(st.last_close)}<br>SMA ${p.fast} ${fmt.num(st.sma_fast)}<br>SMA ${p.slow} ${fmt.num(st.sma_slow)}`;

    $("t-cagr").textContent = fmt.pct(s.cagr); $("t-cagr").className = `value ${s.cagr >= b.cagr ? "up" : "down"}`;
    $("t-bh").textContent = `buy & hold ${fmt.pct(b.cagr)}`;
    $("t-sh").textContent = fmt.num(s.sharpe); $("t-sh").className = `value ${s.sharpe >= b.sharpe ? "up" : "down"}`;
    $("t-bhsh").textContent = `buy & hold ${fmt.num(b.sharpe)}`;
    $("t-dd").textContent = fmt.pct(s.max_drawdown, 1); $("t-bhdd").textContent = `buy & hold ${fmt.pct(b.max_drawdown, 1)}`;
    $("t-exp").textContent = fmt.pct(s.exposure, 0); $("t-trades").textContent = `${s.n_trades} trades · ${p.cost_bps} bps`;

    const x = S.dates, gold = d.crosses.filter((c) => c.type === "golden"), death = d.crosses.filter((c) => c.type === "death");
    plot("c-px", [
      { x, y: S.close, name: p.ticker, line: { color: "rgba(236,235,230,0.55)", width: 1 }, hovertemplate: "%{y:.2f}" },
      { x, y: S.sma_fast, name: `SMA ${p.fast}`, line: { color: C.accent2, width: 1.8 }, hovertemplate: "%{y:.2f}" },
      { x, y: S.sma_slow, name: `SMA ${p.slow}`, line: { color: C.warn, width: 1.8 }, hovertemplate: "%{y:.2f}" },
      { x: gold.map((c) => c.date), y: gold.map((c) => c.price), mode: "markers", name: "Golden cross", marker: { symbol: "triangle-up", size: 12, color: C.up, line: { color: "#000", width: 1 } }, hovertemplate: "Golden %{x}<extra></extra>" },
      { x: death.map((c) => c.date), y: death.map((c) => c.price), mode: "markers", name: "Death cross", marker: { symbol: "triangle-down", size: 12, color: C.down, line: { color: "#000", width: 1 } }, hovertemplate: "Death %{x}<extra></extra>" },
    ], { yaxis: { type: "log", dtick: "D2" } });

    plot("c-eq", [
      { x, y: S.eq_strategy, name: "SMA strategy", line: { color: C.accent2, width: 2 }, hovertemplate: "%{y:.2f}" },
      { x, y: S.eq_buy_hold, name: "Buy & hold", line: { color: C.ink3, width: 1.5 }, hovertemplate: "%{y:.2f}" },
    ], { yaxis: { type: "log", dtick: "D2" } });
    plot("c-dd", [
      { x, y: S.dd_buy_hold, name: "Buy & hold", fill: "tozeroy", fillcolor: "rgba(255,107,107,0.12)", line: { color: C.down, width: 1 }, hovertemplate: "%{y:.1%}" },
      { x, y: S.dd_strategy, name: "SMA strategy", fill: "tozeroy", fillcolor: "rgba(155,107,255,0.18)", line: { color: C.accent2, width: 1.2 }, hovertemplate: "%{y:.1%}" },
    ], { yaxis: { tickformat: ".0%" } });

    $("comp").innerHTML = `<tr><th>Variant</th><th>CAGR</th><th>Total</th><th>Vol</th><th>Sharpe</th><th>Sortino</th><th>Max DD</th><th>Calmar</th></tr>` +
      d.comparison.map((r, i) => `<tr${i === 0 ? ' class="hl"' : ""}><td>${r.name}</td><td>${fmt.pct(r.cagr)}</td><td>${fmt.pct(r.total_return, 0)}</td><td>${fmt.pct(r.volatility, 1)}</td><td>${fmt.num(r.sharpe)}</td><td>${fmt.num(r.sortino)}</td><td>${fmt.pct(r.max_drawdown, 1)}</td><td>${fmt.num(r.calmar)}</td></tr>`).join("");
    $("comp-text").innerHTML = `<b>How to read:</b> "Look-ahead" trades on the same day as the signal, which is impossible in real life. It adds ${fmt.spct(s.lookahead_bias)} a year; ignoring costs adds ${fmt.spct(s.cost_drag)} a year. The realistic line is the one that counts.`;

    const yrs = d.yearly.map((y) => String(y.year)), ex = d.yearly.map((y) => y.strategy - y.buy_hold);
    plot("c-year", [{
      type: "bar", x: yrs, y: ex, name: "Excess vs B&H",
      marker: { color: ex.map((v) => (v >= 0 ? C.up : C.down)), opacity: d.yearly.map((y) => (y.regime === "trending" ? 1 : 0.55)) },
      customdata: d.yearly.map((y) => [y.strategy, y.buy_hold, y.regime]),
      hovertemplate: "%{x} · %{customdata[2]}<br>Strategy %{customdata[0]:.1%}<br>Buy & hold %{customdata[1]:.1%}<br>Excess %{y:.1%}<extra></extra>",
    }], { yaxis: { tickformat: ".0%" }, showlegend: false, hovermode: "closest" });

    const helps = s.max_drawdown > b.max_drawdown;
    $("conclusion").textContent = `On ${p.ticker} since ${p.start.slice(0, 4)}: ${fmt.pct(s.cagr)} a year for the strategy vs ${fmt.pct(b.cagr)} for buy & hold. `
      + (s.cagr >= b.cagr ? "The strategy earned more. " : "Buy & hold earned more. ")
      + (helps ? `But the worst fall was ${fmt.pct(s.max_drawdown, 0)} instead of ${fmt.pct(b.max_drawdown, 0)}: the strategy mainly reduces risk.` : `Its worst fall was ${fmt.pct(s.max_drawdown, 0)} vs ${fmt.pct(b.max_drawdown, 0)}.`);
  }

  run();
})();
