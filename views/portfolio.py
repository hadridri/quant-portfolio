import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant import portfolio
from views.common import (BLUE, GREY, GREEN, ORANGE, RED, DataError, active, get_returns, get_var, label, md, money, num,
                          pct, save_portfolio, set_active, show_chart, ticker_options)

st.title("Portfolio & VaR")

# ---------- Step 1 ----------
st.header("Step 1. Build your portfolio")
pf = active()
tickers = st.multiselect("Tickers (pick from the list, or type any Yahoo Finance symbol and press Enter)",
                         ticker_options(*pf["weights"]), default=list(pf["weights"]), format_func=label,
                         accept_new_options=True, max_selections=30)
tickers = [t.strip().upper() for t in tickers]
as_amount = st.radio("Allocation in", ["% of the portfolio", "Amount ($)"], horizontal=True) == "Amount ($)"

if tickers:
    column = "Amount ($)" if as_amount else "Weight (%)"
    weights = pf["weights"]
    start = [weights.get(t, 0) for t in tickers]
    if sum(start) <= 0:
        start = [1] * len(tickers)
    start = np.array(start, dtype=float) / sum(start)
    table = pd.DataFrame({"Ticker": tickers, column: np.round(start * (pf["notional"] if as_amount else 100), 2)})
    edited = st.data_editor(table, hide_index=True, disabled=["Ticker"], width="content",
                            key=f"alloc-{'-'.join(tickers)}-{as_amount}-{pf['name']}")
    values = edited[column].fillna(0).clip(lower=0).values
    total = float(values.sum())

    if as_amount:
        notional = total
        st.caption(md(f"Total invested: {money(total)}"))
    else:
        notional = st.number_input("Amount invested ($)", min_value=1.0, value=float(pf["notional"]), step=1000.0)
        if abs(total - 100) > 0.01:
            st.warning(f"The weights add up to {total:.1f}%. They will be rescaled to 100%.")

    if st.button("Create portfolio", type="primary", disabled=total <= 0):
        set_active("My portfolio", {t: float(v / total) for t, v in zip(tickers, values) if v > 0}, float(notional))
        st.session_state.pop("optimised", None)
        st.rerun()

names = tuple(pf["weights"])
w = np.array([pf["weights"][t] for t in names])
if len(names) < 2:
    st.info("Add at least two tickers to analyse a portfolio.")
    st.stop()

try:
    with st.spinner("Loading prices from Yahoo Finance..."):
        rets = get_returns(names)
        spy = get_returns(("SPY", "TLT"))["SPY"]
except DataError as e:
    st.error(str(e))
    st.stop()

last_day = rets.index[-1].strftime("%d %b %Y")
first_day = rets.index[0].strftime("%d %b %Y")

# ---------- Step 2 ----------
st.header("Step 2. Backtest")
rf = st.session_state.get("rf", 3.0) / 100
result = portfolio.backtest(rets, w, rf, spy)
s, b = result["stats"], result["benchmark_stats"]
c = st.columns(4)
c[0].metric("Return per year", pct(s["cagr"]), f"S&P 500: {pct(b['cagr'])}", delta_color="off")
c[1].metric("Volatility", pct(s["volatility"]), f"S&P 500: {pct(b['volatility'])}", delta_color="off")
c[2].metric("Sharpe ratio", num(s["sharpe"]), f"S&P 500: {num(b['sharpe'])}", delta_color="off",
            help="Return above the risk-free rate, per unit of risk. Above 1 is good.")
c[3].metric("Worst fall", pct(s["max_drawdown"]), f"S&P 500: {pct(b['max_drawdown'])}", delta_color="off")

fig = go.Figure()
fig.add_scatter(x=rets.index, y=(1 + result["returns"]).cumprod() * pf["notional"], name=pf["name"], line=dict(color=BLUE, width=2))
fig.add_scatter(x=rets.index, y=(1 + result["benchmark"]).cumprod() * pf["notional"], name="S&P 500", line=dict(color=GREY, width=1.5))
fig.update_yaxes(tickprefix="$", tickformat=",.0f")
show_chart(fig)
st.caption(f"Value of the portfolio from {first_day} to {last_day}, with fixed weights. Drag or scroll on a chart to zoom, double-click to reset.")

# ---------- Step 3 ----------
st.header("Step 3. Risk")
left, right = st.columns(2)
with left:
    st.subheader("Value at Risk, next month")
    conf = st.select_slider("Confidence", [0.90, 0.95, 0.99], value=0.95, format_func=lambda x: f"{x:.0%}")
    with st.spinner("Simulating 10,000 months..."):
        mc = get_var(names, tuple(w), pf["notional"], 21, conf)
    r = mc["risk"]
    a, e = st.columns(2)
    a.metric(f"VaR {conf:.0%}", money(r["mc_var_cash"]), f"-{pct(r['mc_var'])}", delta_color="inverse",
             help="The model simulates 10,000 possible months. This is the loss exceeded only in the worst cases.")
    e.metric("Expected shortfall", money(r["mc_es_cash"]), f"-{pct(r['mc_es'])}", delta_color="inverse",
             help="The average loss in those worst cases.")
    st.write(md(f"In a bad month ({1 - conf:.0%} of cases) you lose more than **{money(r['mc_var_cash'])}**. "
                f"When that happens, the average loss is **{money(r['mc_es_cash'])}**."))

    edges = np.array(mc["distribution"]["edges"])
    mids = (edges[:-1] + edges[1:]) / 2
    fig = go.Figure(go.Bar(x=mids, y=mc["distribution"]["counts"], marker_color=[RED if m <= -r["mc_var"] else BLUE for m in mids]))
    fig.update_xaxes(tickformat=".0%", title="Simulated return over one month")
    fig.update_yaxes(title="Simulations")
    fig.update_layout(bargap=0.03)
    show_chart(fig, height=300, selector=False)
    st.caption("Red bars: the worst months. VaR is where they start.")

with right:
    st.subheader("Correlation matrix")
    notes = portfolio.correlation_notes(rets, w)
    corr = notes["corr"]
    fig = go.Figure(go.Heatmap(z=corr.values, x=list(corr.columns), y=list(corr.index), zmin=-1, zmax=1, colorscale="RdBu_r",
                               text=corr.round(2).values, texttemplate="%{text}", showscale=False))
    fig.update_yaxes(autorange="reversed")
    show_chart(fig, height=420, selector=False)
    st.caption("1 = move together, 0 = independent, -1 = opposite. Low numbers mean real diversification.")
    if notes["high"]:
        pairs_text = ", ".join(f"{x} and {y} ({v:.2f})" for x, y, v in notes["high"][:5])
        st.warning(f"These holdings behave almost like one bet: {pairs_text}. Keeping both adds little diversification.")
    elif notes["average"] < 0.4:
        st.success(f"Well spread: the average correlation is {notes['average']:.2f}.")
    else:
        st.info(f"Average correlation: {notes['average']:.2f}. Adding bonds or gold usually lowers it.")

# ---------- Step 4 ----------
st.header("Step 4. Find the best allocation")
st.write("Python tests your tickers and looks for the weights with the highest Sharpe ratio.")
a, b2 = st.columns(2)
cap = a.slider("Maximum weight per ticker", 10, 100, 40, step=5, format="%d%%",
               help="Stops the optimiser from putting everything on one stock.") / 100
rf_pct = b2.number_input("Risk-free rate (%)", 0.0, 10.0, 3.0, step=0.25, key="rf")

if st.button("Find the best allocation", type="primary"):
    with st.spinner("Testing allocations..."):
        st.session_state.optimised = {"key": (names, cap, rf_pct), "result": portfolio.optimise(rets, w, rf_pct / 100, cap)}

opt = st.session_state.get("optimised")
if opt and opt["key"] == (names, cap, rf_pct):
    res = opt["result"]
    wt = res["weights"]
    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        fig.add_bar(y=wt.index, x=wt["Yours"], name="Yours", orientation="h", marker_color=GREY)
        fig.add_bar(y=wt.index, x=wt["Max Sharpe"], name="Best Sharpe", orientation="h", marker_color=BLUE)
        fig.update_xaxes(tickformat=".0%")
        fig.update_yaxes(autorange="reversed")
        show_chart(fig, height=max(280, 40 * len(wt)), selector=False)
    with right:
        ins = res["in_sample"]
        st.dataframe(pd.DataFrame({
            "Your allocation": [pct(ins["Yours"]["cagr"]), pct(ins["Yours"]["volatility"]), num(ins["Yours"]["sharpe"]), pct(ins["Yours"]["max_drawdown"])],
            "Best Sharpe": [pct(ins["Max Sharpe"]["cagr"]), pct(ins["Max Sharpe"]["volatility"]), num(ins["Max Sharpe"]["sharpe"]), pct(ins["Max Sharpe"]["max_drawdown"])],
            "Lowest risk": [pct(ins["Min variance"]["cagr"]), pct(ins["Min variance"]["volatility"]), num(ins["Min variance"]["sharpe"]), pct(ins["Min variance"]["max_drawdown"])],
        }, index=["Return per year", "Volatility", "Sharpe ratio", "Worst fall"]))
        st.caption("Computed on the same history used to choose the weights, so these figures are flattering.")

    if res["out_of_sample"]:
        st.subheader("Would it have worked for real?")
        st.write(f"Each quarter since {res['oos_start']:%b %Y}, the weights are chosen using the two previous years only, "
                 "then tested on the following quarter. No future data is used.")
        curves = res["oos_curves"]
        colours = {"Your allocation": GREY, "Equal weights": ORANGE}
        fig = go.Figure()
        for name in curves:
            fig.add_scatter(x=curves.index, y=curves[name], name=name, line=dict(color=colours.get(name), width=2))
        show_chart(fig, height=340)
        oos = res["out_of_sample"]
        st.dataframe(pd.DataFrame({k: {"Return per year": pct(v["cagr"]), "Volatility": pct(v["volatility"]), "Sharpe ratio": num(v["sharpe"]),
                                       "Worst fall": pct(v["max_drawdown"])} for k, v in oos.items()}).T)
        winner = max(oos, key=lambda k: oos[k]["sharpe"])
        st.write(f"Best real-world Sharpe ratio: **{winner}** ({num(oos[winner]['sharpe'])}).")
    else:
        st.info("At least three years of common history are needed for the real-world test.")

    # ---------- Step 5 ----------
    st.header("Step 5. Use and save")
    for title, column, name in [("Use the best Sharpe allocation", "Max Sharpe", "Best Sharpe portfolio"),
                                ("Use the lowest risk allocation", "Min variance", "Lowest risk portfolio")]:
        chosen = {t: float(v) for t, v in wt[column].items() if v >= 0.005}
        total = sum(chosen.values())
        chosen = {t: v / total for t, v in chosen.items()}
        st.write(f"{name}: " + ", ".join(f"**{t}** {v:.0%}" for t, v in chosen.items()))
        if st.button(title):
            set_active(name, chosen, pf["notional"])
            st.session_state.pop("optimised", None)
            st.rerun()

st.subheader("Save the active portfolio")
name = st.text_input("Portfolio name", placeholder="My long-term portfolio")
if st.button("Save portfolio", disabled=not name.strip()):
    save_portfolio(name.strip(), pf["weights"], pf["notional"])
    set_active(name.strip(), pf["weights"], pf["notional"])
    st.rerun()
st.caption("Saved in this browser, and recomputed with the latest prices each time you open it. Find your portfolios in the left panel.")
