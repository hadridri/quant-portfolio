"""Project 2 - Pairs trading / statistical arbitrage.

Pipeline
    1. Engle-Granger cointegration test on log prices (statsmodels.coint).
    2. Hedge ratio by OLS:  log A = alpha + beta * log B + spread.
       The backtest uses a *rolling* OLS so the hedge ratio on day t only uses
       data up to t (no look-ahead). The full-sample beta is reported too.
    3. z-score of the spread on a rolling window.
    4. Signals: z < -entry -> long spread, z > +entry -> short spread,
       |z| < exit -> flat, |z| > stop -> forced exit (relationship may have
       broken; re-armed only once |z| is back inside the exit band).
    5. Half-life of mean reversion from an Ornstein-Uhlenbeck / AR(1) fit,
       transaction costs on every leg, and a rolling cointegration check.

Run in Spyder (F5) to backtest KO / PEP.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint

from .data import DataError, dates, get_prices, perf_stats, to_json_safe


def half_life(spread: pd.Series) -> float:
    s = spread.dropna()
    lag = s.shift(1).dropna()
    delta = (s - s.shift(1)).dropna()
    b = sm.OLS(delta.values, sm.add_constant(lag.values)).fit().params[1]
    return -np.log(2) / b if b < 0 else np.inf


def rolling_hedge(y: pd.Series, x: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """Rolling OLS y = a + b x using only past and current observations."""
    cov = y.rolling(window).cov(x)
    var = x.rolling(window).var()
    beta = cov / var
    alpha = y.rolling(window).mean() - beta * x.rolling(window).mean()
    return alpha, beta


def generate_positions(z: pd.Series, entry: float, exit_: float, stop: float) -> tuple[pd.Series, list]:
    pos = np.zeros(len(z))
    events = []
    current, armed = 0, True
    for i, (d, zi) in enumerate(z.items()):
        if np.isnan(zi):
            pos[i] = 0
            continue
        if not armed and abs(zi) < exit_:
            armed = True
        if current != 0:
            if abs(zi) > stop:
                events.append({"date": d, "type": "stop", "z": zi})
                current, armed = 0, False
            elif abs(zi) < exit_:
                events.append({"date": d, "type": "exit", "z": zi})
                current = 0
        elif armed:
            if zi < -entry and zi > -stop:
                current = 1
                events.append({"date": d, "type": "long", "z": zi})
            elif zi > entry and zi < stop:
                current = -1
                events.append({"date": d, "type": "short", "z": zi})
        pos[i] = current
    return pd.Series(pos, index=z.index), events


def run(ticker_a: str = "KO", ticker_b: str = "PEP", period: str = "5y", window: int = 30,
        hedge_window: int = 120, entry: float = 2.0, exit_: float = 0.5, stop: float = 3.5,
        cost_bps: float = 5.0, rolling: bool = True, closes: pd.DataFrame | None = None) -> dict:
    """`closes` (optional): preloaded close prices, used by build_static.py to avoid
    one download per pair."""
    ticker_a, ticker_b = ticker_a.strip().upper(), ticker_b.strip().upper()
    if ticker_a == ticker_b:
        raise DataError("Choose two different tickers.")
    if not (0 <= exit_ < entry < stop):
        raise DataError("Thresholds must satisfy 0 <= exit < entry < stop.")
    window = int(np.clip(window, 5, 250))
    hedge_window = int(np.clip(hedge_window, 30, 500))
    min_obs = hedge_window + window + 60

    if closes is None:
        prices = get_prices([ticker_a, ticker_b], period=period, min_obs=min_obs)
    else:
        prices = closes[[ticker_a, ticker_b]].dropna()
        prices = prices[prices.index >= prices.index[-1] - pd.DateOffset(years=int(period[:-1]))]
        if len(prices) < min_obs:
            raise DataError(f"Only {len(prices)} common trading days for {ticker_a} / {ticker_b}.")
    a, b = prices.columns
    ly, lx = np.log(prices[a]), np.log(prices[b])

    # 1. Cointegration (full sample, both directions)
    t_stat, p_value, crit = coint(ly, lx)
    p_reverse = coint(lx, ly)[1]

    # 2. Hedge ratio
    ols = sm.OLS(ly, sm.add_constant(lx)).fit()
    alpha_s, beta_s = ols.params.iloc[0], ols.params.iloc[1]
    static_spread = ly - alpha_s - beta_s * lx
    adf_p = adfuller(static_spread.dropna(), autolag="AIC")[1]
    hl = half_life(static_spread)

    if rolling:
        alpha_r, beta_r = rolling_hedge(ly, lx, hedge_window)
        # Use yesterday's hedge so today's spread is tradeable with known parameters
        spread = ly - alpha_r.shift(1) - beta_r.shift(1) * lx
        beta_t = beta_r.shift(1)
    else:
        spread = static_spread
        beta_t = pd.Series(beta_s, index=ly.index)

    # 3. z-score
    z = (spread - spread.rolling(window).mean()) / spread.rolling(window).std()

    # 4. Signals (decided at the close of day t)
    pos, events = generate_positions(z, entry, exit_, stop)

    # 5. Backtest: trade at next close. Long spread = +1 A, -beta B,
    #    gross exposure normalised to 1 (1 + |beta| dollars).
    ra, rb = prices[a].pct_change(), prices[b].pct_change()
    held = pos.shift(1).fillna(0)
    beta_held = beta_t.shift(1).bfill()
    gross = 1 + beta_held.abs()
    gross_ret = held * (ra - beta_held * rb) / gross
    turnover = held.diff().abs().fillna(held.abs())
    costs = turnover * cost_bps / 1e4 * 2          # two legs per change
    net_ret = (gross_ret - costs).fillna(0)
    equity = (1 + net_ret).cumprod()

    # Trade-level stats
    trades, entry_i = [], None
    eq_vals = equity.values
    for i in range(1, len(held)):
        if held.iloc[i] != 0 and held.iloc[i - 1] == 0:
            entry_i = i - 1
        elif held.iloc[i] == 0 and held.iloc[i - 1] != 0 and entry_i is not None:
            trades.append({"entry": held.index[entry_i], "exit": held.index[i],
                           "side": "long" if held.iloc[i - 1] > 0 else "short",
                           "pnl": eq_vals[i] / eq_vals[entry_i] - 1, "days": i - entry_i})
            entry_i = None
    wins = [t for t in trades if t["pnl"] > 0]

    # Rolling 1-year cointegration p-value: does the relationship hold over time?
    roll_p_dates, roll_p = [], []
    for end in range(252, len(ly), 21):
        roll_p_dates.append(ly.index[end])
        roll_p.append(coint(ly.iloc[end - 252:end], lx.iloc[end - 252:end])[1])

    stats = perf_stats(net_ret)
    stats.update({
        "n_trades": len(trades), "win_rate": len(wins) / len(trades) if trades else None,
        "avg_trade": np.mean([t["pnl"] for t in trades]) if trades else None,
        "avg_holding_days": np.mean([t["days"] for t in trades]) if trades else None,
        "time_in_market": (held != 0).mean(), "total_costs": costs.sum(),
    })

    cointegrated = p_value < 0.05
    hl_ok = 5 <= hl <= 30
    if cointegrated and hl_ok:
        verdict = ("Tradeable", f"Linked (p = {p_value:.3f}) and the gap closes by half in about {hl:.0f} days.")
    elif cointegrated:
        verdict = ("Caution", f"Linked (p = {p_value:.3f}), but the gap takes {hl:.0f} days to close by half (ideal: 5-30).")
    else:
        verdict = ("Not linked", f"p-value {p_value:.3f} is above 0.05: nothing says the gap will close.")

    pts = lambda ev: [e for e in events if e["type"] == ev]
    result = {
        "params": {"a": a, "b": b, "period": period, "window": window, "hedge_window": hedge_window,
                   "entry": entry, "exit": exit_, "stop": stop, "cost_bps": cost_bps, "rolling": rolling,
                   "start": prices.index[0].strftime("%Y-%m-%d"), "end": prices.index[-1].strftime("%Y-%m-%d")},
        "tests": {"coint_t": t_stat, "coint_p": p_value, "coint_p_reverse": p_reverse,
                  "crit_1": crit[0], "crit_5": crit[1], "crit_10": crit[2],
                  "adf_p": adf_p, "beta": beta_s, "alpha": alpha_s, "r2": ols.rsquared,
                  "half_life": hl, "beta_latest": beta_t.iloc[-1], "z_latest": z.iloc[-1],
                  "position_latest": int(pos.iloc[-1])},
        "verdict": {"label": verdict[0], "text": verdict[1]},
        "stats": stats,
        "series": {
            "dates": dates(prices.index),
            "a100": (prices[a] / prices[a].iloc[0] * 100).values,
            "b100": (prices[b] / prices[b].iloc[0] * 100).values,
            "spread": spread.values, "z": z.values, "position": pos.values,
            "equity": equity.values, "beta": beta_t.values,
        },
        "events": {k: {"dates": [e["date"] for e in pts(k)], "z": [e["z"] for e in pts(k)]}
                   for k in ("long", "short", "exit", "stop")},
        "trades": trades[-25:],
        "rolling_coint": {"dates": roll_p_dates, "p": roll_p},
    }
    return to_json_safe(result)


if __name__ == "__main__":
    res = run("KO", "PEP")
    t, s = res["tests"], res["stats"]
    print(f"\n{res['params']['a']} / {res['params']['b']}  {res['params']['start']} -> {res['params']['end']}")
    print(f"Engle-Granger p-value : {t['coint_p']:.4f}   ADF on spread: {t['adf_p']:.4f}")
    print(f"Hedge ratio (OLS)     : {t['beta']:.3f}    R2 {t['r2']:.2f}")
    print(f"Half-life             : {t['half_life']:.1f} days")
    print(f"Verdict               : {res['verdict']['label']} - {res['verdict']['text']}")
    print(f"\nTrades {s['n_trades']}, win rate {s['win_rate'] or 0:.0%}, Sharpe {s['sharpe']:.2f}, "
          f"CAGR {s['cagr']:.2%}, MaxDD {s['max_drawdown']:.2%}")
