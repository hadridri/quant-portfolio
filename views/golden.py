import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from views.common import (BLUE, GREEN, GREY, NAMES, ORANGE, RED, DataError, active, get_alert_status, get_scan, get_sma,
                          get_sma_portfolio, label, md, num, pct, show_chart, ticker_options)

st.title("Golden cross")
st.write("Golden cross: the 50-day average moves above the 200-day average, the trend turns up. Death cross: the opposite.")

# ---------- E-mail alerts ----------
st.header("E-mail alerts")
status = get_alert_status()
if status:
    st.success(f"Active. {len(status['rows'])} tickers are checked several times a day and an e-mail is sent on each new cross. "
               f"Last check: {status['checked_at']} UTC.")
    if status["history"]:
        alerts = pd.DataFrame(status["history"][:10])
        alerts["type"] = alerts["type"].map({"golden": "Golden cross", "death": "Death cross"})
        alerts["ticker"] = alerts["ticker"].map(label)
        st.dataframe(alerts.rename(columns={"time": "Time (UTC)", "ticker": "Ticker", "type": "Signal", "price": "Price"}), hide_index=True)
    else:
        st.caption("No cross detected yet since the alerts started.")
else:
    st.warning("Alert status is not available right now.")

# ---------- Scanner ----------
st.header("Scanner")
try:
    with st.spinner("Scanning every ticker..."):
        scan = get_scan()
except Exception:
    scan = pd.DataFrame(status["rows"]) if status else pd.DataFrame()
if scan.empty:
    st.error("Yahoo Finance is not responding. Try Refresh in a moment.")
    st.stop()

left, right = st.columns([3, 1])
view = left.segmented_control("Show", ["New golden crosses", "New death crosses", "Close to crossing", "All"],
                              default="New golden crosses", label_visibility="collapsed") or "All"
mine = right.toggle("My portfolio only")

table = scan.copy()
recent = table["sessions_since"].fillna(9999) <= 30
if view == "New golden crosses":
    table = table[recent & (table["sign"] > 0)].sort_values("sessions_since")
elif view == "New death crosses":
    table = table[recent & (table["sign"] < 0)].sort_values("sessions_since")
elif view == "Close to crossing":
    table = table[table["gap"].abs() < 0.02].assign(order=lambda d: d["gap"].abs()).sort_values("order")
else:
    table = table.sort_values("ticker")
if mine:
    table = table[table["ticker"].isin(active()["weights"])]

st.dataframe(pd.DataFrame({
    "Ticker": table["ticker"], "Name": table["ticker"].map(lambda t: NAMES.get(t, t)), "Price": table["price"].round(2),
    "SMA 50": table["sma_fast"].round(2), "SMA 200": table["sma_slow"].round(2),
    "Gap": (table["gap"] * 100).round(2).astype(str) + "%",
    "Trend": table["sign"].map({1: "Golden", -1: "Death"}), "Last cross": table["last_cross"],
    "Sessions ago": table["sessions_since"],
}), hide_index=True, width="stretch", height=320)
st.caption(f"{len(scan)} tickers. 'New' means crossed in the last 30 sessions. Gap = distance between SMA 50 and SMA 200. "
           "Today's price counts as the close until the market shuts, so a cross on the day can still reverse.")

# ---------- Detail ----------
st.header("Detail, last 5 years")
pf = active()
PORTFOLIO = "My portfolio"
choice = st.selectbox("Ticker", [PORTFOLIO, *ticker_options("SPY")], index=1, format_func=lambda t: f"{PORTFOLIO}: {pf['name']}" if t == PORTFOLIO else label(t),
                      accept_new_options=True)
try:
    with st.spinner("Loading prices from Yahoo Finance..."):
        if choice == PORTFOLIO:
            res = get_sma_portfolio(tuple(pf["weights"]), tuple(pf["weights"].values()))
        else:
            res = get_sma(choice.strip().upper())
except DataError as e:
    st.error(str(e))
    st.stop()

st_, s, b, S = res["status"], res["strategy"], res["buy_hold"], res["series"]
gold = st_["regime"] == "bullish"
days = st_["days_since_cross"]
since = f" Last cross: {st_['last_cross']['date']}, {days} sessions ago." if st_["last_cross"] else ""
message = f"SMA 50 is {pct(abs(st_['gap']))} {'above' if gold else 'below'} SMA 200.{since}"
(st.success if gold else st.error)(f"{'Golden' if gold else 'Death'} cross trend. {message}")

fig = go.Figure()
fig.add_scatter(x=S["dates"], y=S["close"], name="Price", line=dict(color=GREY, width=1))
fig.add_scatter(x=S["dates"], y=S["sma_fast"], name="SMA 50", line=dict(color=BLUE, width=2))
fig.add_scatter(x=S["dates"], y=S["sma_slow"], name="SMA 200", line=dict(color=ORANGE, width=2))
for kind, symbol, colour, name in [("golden", "triangle-up", GREEN, "Golden cross"), ("death", "triangle-down", RED, "Death cross")]:
    hits = [c for c in res["crosses"] if c["type"] == kind]
    fig.add_scatter(x=[c["date"] for c in hits], y=[c["price"] for c in hits], mode="markers", name=name,
                    marker=dict(symbol=symbol, size=13, color=colour, line=dict(color="white", width=1)))
show_chart(fig, height=460, last_days=730)

c = st.columns(4)
c[0].metric("Strategy, per year", pct(s["cagr"]), f"Buy & hold: {pct(b['cagr'])}", delta_color="off")
c[1].metric("Sharpe ratio", num(s["sharpe"]), f"Buy & hold: {num(b['sharpe'])}", delta_color="off")
c[2].metric("Worst fall", pct(s["max_drawdown"]), f"Buy & hold: {pct(b['max_drawdown'])}", delta_color="off")
c[3].metric("Trades", s["n_trades"], f"Invested {pct(s['exposure'], 0)} of the time", delta_color="off")

fig = go.Figure()
fig.add_scatter(x=S["dates"], y=S["eq_strategy"], name="Strategy", line=dict(color=BLUE, width=2))
fig.add_scatter(x=S["dates"], y=S["eq_buy_hold"], name="Buy & hold", line=dict(color=GREY, width=1.5))
show_chart(fig, height=300)
st.caption(md(f"Growth of $1 from {res['params']['start']} to {res['params']['end']}: buy the day after a golden cross, sell the day after a death cross, 0.1% cost per trade."))
