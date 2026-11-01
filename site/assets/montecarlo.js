(() => {
  const { fmt, load, setMode, colors: C, plot } = Q;
  const $ = (id) => document.getElementById(id);
  const DEFAULT = "AAPL,MSFT,JPM,XOM,JNJ";

  $("alpha").addEventListener("input", (e) => ($("alpha-out").textContent = `${Math.round(e.target.value * 100)}%`));
  document.querySelectorAll(".presets button").forEach((b) => b.addEventListener("click", () => {
    $("tickers").value = b.dataset.t; $("weights").value = ""; run();
  }));
  $("form").addEventListener("submit", (e) => { e.preventDefault(); run(); });

  async function run() {
    const q = new URLSearchParams({
      tickers: $("tickers").value.replace(/\s/g, ""), period: $("period").value, horizon: $("horizon").value,
      alpha: $("alpha").value, sims: $("sims").value, notional: $("notional").value,
    });
    if ($("weights").value.trim()) q.set("weights", $("weights").value.replace(/\s/g, ""));
    const isDefault = q.get("tickers").toUpperCase() === DEFAULT && !q.has("weights") && q.get("period") === "3y"
      && q.get("horizon") === "21" && q.get("alpha") === "0.95" && q.get("sims") === "10000" && q.get("notional") === "1000000";

    $("results").classList.add("loading"); $("run").disabled = true; $("error").classList.remove("show");
    try {
      const { data, mode } = await load(`/api/montecarlo?${q}`, isDefault ? "montecarlo" : null);
      setMode($("mode"), mode, `· ${data.params.end}`);
      render(data);
    } catch (err) {
      $("error").textContent = err.message; $("error").classList.add("show");
    } finally {
      $("results").classList.remove("loading"); $("run").disabled = false;
    }
  }

  function render(d) {
    const r = d.risk, p = d.params, N = p.notional, conf = Math.round(p.alpha * 100);
    $("t-var-l").textContent = `VaR ${conf}% · ${p.horizon}d`;
    $("t-var").textContent = fmt.pct(r.mc_var); $("t-var-c").textContent = fmt.money(r.mc_var_cash);
    $("t-es").textContent = fmt.pct(r.mc_es); $("t-es-c").textContent = fmt.money(r.mc_es_cash);
    $("t-pl").textContent = fmt.pct(r.prob_loss, 1); $("t-er").textContent = `E[R] ${fmt.spct(r.expected_return)}`;
    $("t-dr").textContent = `${fmt.num(r.diversification_ratio)}×`; $("t-rho").textContent = `avg ρ ${fmt.num(d.avg_corr)}`;

    // Fan chart
    const days = d.fan.days, P = d.fan.pct, v = (a) => a.map((x) => x * N);
    const band = (lo, hi, op, name) => [
      { x: days, y: v(P[lo]), line: { width: 0 }, hoverinfo: "skip", showlegend: false },
      { x: days, y: v(P[hi]), fill: "tonexty", fillcolor: `rgba(155,107,255,${op})`, line: { width: 0 }, name, hoverinfo: "skip" },
    ];
    const samples = d.fan.samples.map((s) => ({
      x: days, y: v(s), mode: "lines", line: { width: 0.6, color: "rgba(236,235,230,0.10)" }, hoverinfo: "skip", showlegend: false,
    }));
    const lowP = String(100 - conf <= 1 ? 1 : 5);
    plot("c-fan", [...samples, ...band("1", "99", 0.08, "1–99%"), ...band("5", "95", 0.14, "5–95%"), ...band("25", "75", 0.22, "25–75%"),
      { x: days, y: v(P["50"]), name: "Median", line: { color: C.accent2, width: 2 } },
      { x: days, y: v(P[lowP]), name: `${lowP}th pct`, line: { color: C.down, width: 1.5, dash: "dot" } }],
      { yaxis: { tickprefix: "$", tickformat: ",.0f" }, xaxis: { title: { text: "Trading days" } }, margin: { l: 80 } });

    // Distribution
    const e = d.distribution.edges, mids = e.slice(0, -1).map((x, i) => (x + e[i + 1]) / 2);
    plot("c-dist", [{
      type: "bar", x: mids, y: d.distribution.counts, hovertemplate: "%{x:.2%}: %{y}<extra></extra>",
      marker: { color: mids.map((m) => (m <= -r.mc_var ? C.down : "rgba(197,168,255,0.55)")) },
    }], {
      bargap: 0.05, hovermode: "closest", xaxis: { tickformat: ".0%" }, showlegend: false,
      shapes: [vline(-r.mc_var, C.down), vline(-r.mc_es, C.warn)],
      annotations: [ann(-r.mc_var, `VaR ${fmt.pct(r.mc_var, 1)}`, C.down, 1), ann(-r.mc_es, `ES ${fmt.pct(r.mc_es, 1)}`, C.warn, 0.88)],
    });

    // Correlation heatmap
    const t = p.tickers;
    plot("c-corr", [{
      type: "heatmap", z: d.corr, x: t, y: t, zmin: -1, zmax: 1, colorscale: [[0, "#2b6cff"], [0.5, "#121418"], [1, C.accent]],
      text: d.corr.map((row) => row.map((x) => x.toFixed(2))), texttemplate: "%{text}", hovertemplate: "%{y} / %{x}: %{z:.2f}<extra></extra>",
      colorbar: { thickness: 8, outlinewidth: 0 },
    }], { hovermode: "closest", yaxis: { autorange: "reversed" }, margin: { l: 64, b: 56 } });

    // Sensitivity
    const s = d.sensitivity, cur = s.find((x) => x.is_current) || s[0];
    plot("c-sens", [
      { x: s.map((x) => x.rho), y: s.map((x) => x.var * N), name: `VaR ${conf}%`, line: { color: C.accent2, width: 2.5 }, hovertemplate: "$%{y:,.0f}" },
      { x: s.map((x) => x.rho), y: s.map((x) => x.es * N), name: "Expected shortfall", line: { color: C.down, width: 2.5 }, hovertemplate: "$%{y:,.0f}" },
      { x: [cur.rho], y: [cur.var * N], mode: "markers+text", marker: { size: 11, color: C.ink }, text: ["today"], textposition: "top left", name: "Current avg ρ", hoverinfo: "skip" },
    ], { xaxis: { title: { text: "Pairwise correlation ρ" } }, yaxis: { tickprefix: "$", tickformat: ",.0f" }, margin: { l: 80 } });
    const hi = s[s.length - 1];
    $("sens-text").textContent = `Moving from today's average ρ of ${fmt.num(cur.rho)} to ${fmt.num(hi.rho)} raises VaR from ${fmt.money(cur.var * N)} to ${fmt.money(hi.var * N)} (×${fmt.num(hi.var / cur.var, 1)}), with the same assets and volatilities.`;

    // Methods
    plot("c-methods", [
      { type: "bar", x: ["Monte Carlo", "Parametric", "Historical"], y: [r.mc_var, r.param_var, r.hist_var], name: "VaR", marker: { color: C.accent2 }, hovertemplate: "%{y:.2%}" },
      { type: "bar", x: ["Monte Carlo", "Parametric", "Historical"], y: [r.mc_es, r.param_es, r.hist_es], name: "ES", marker: { color: C.down }, hovertemplate: "%{y:.2%}" },
    ], { barmode: "group", yaxis: { tickformat: ".1%" }, hovermode: "x" });

    // Stress table
    $("stress").innerHTML = `<tr><th>λ toward ρ=1</th><th>VaR</th><th>ES</th><th>VaR $</th></tr>` + d.stress.map((x) =>
      `<tr${x.lambda === 0 ? ' class="hl"' : ""}><td>${x.lambda === 0 ? "0 · today" : x.lambda}</td><td>${fmt.pct(x.var)}</td><td>${fmt.pct(x.es)}</td><td>${fmt.money(x.var * N)}</td></tr>`).join("");

    // Assets
    $("sample").textContent = `${p.start} → ${p.end} · ${p.n_obs} daily obs`;
    $("assets").innerHTML = `<tr><th>Ticker</th><th>Weight</th><th>Ann. return</th><th>Ann. vol</th><th>Return / vol</th></tr>` + d.assets.map((a) =>
      `<tr><td>${a.ticker}</td><td>${fmt.pct(a.weight, 1)}</td><td class="${fmt.sign(a.ann_return)}">${fmt.spct(a.ann_return)}</td><td>${fmt.pct(a.ann_vol)}</td><td>${fmt.num(a.ann_return / a.ann_vol)}</td></tr>`).join("")
      + `<tr class="hl"><td>Portfolio</td><td>100%</td><td></td><td>${fmt.pct(r.port_ann_vol)}</td><td></td></tr>`;

    // History
    const pal = [C.accent2, C.up, C.warn, "#5fb4ff", C.down, "#ff9ad5", "#9be15d", "#ffd36b"];
    plot("c-hist", t.map((tk, i) => ({ x: d.history.dates, y: d.history.base100[tk], name: tk, line: { width: 1.5, color: pal[i % pal.length] } })),
      { yaxis: { title: { text: "Base 100" } } });

    const fat = r.hist_var > r.mc_var;
    $("takeaway").textContent = `Over ${p.horizon} trading days, this ${t.length}-asset portfolio has a ${100 - conf}% chance of losing more than ${fmt.money(r.mc_var_cash)} on ${fmt.money(N)}, and in that tail the average loss is ${fmt.money(r.mc_es_cash)}. `
      + `Diversification cuts volatility by a factor of ${fmt.num(r.diversification_ratio)} compared with holding the assets in isolation, but that benefit depends on correlations staying where they are. `
      + (fat ? `Historical VaR (${fmt.pct(r.hist_var)}) is above the Gaussian Monte Carlo figure, so the real data has fatter tails than the model assumes.`
             : `Historical VaR (${fmt.pct(r.hist_var)}) is below the Monte Carlo figure over this sample, so the model is conservative here. A calm sample period can make it look more prudent than it really is.`);
  }

  const vline = (x, color) => ({ type: "line", x0: x, x1: x, yref: "paper", y0: 0, y1: 1, line: { color, width: 1.5, dash: "dash" } });
  const ann = (x, text, color, y) => ({ x, y, yref: "paper", text, showarrow: false, xanchor: "right", font: { color, size: 11 } });

  run();
})();
