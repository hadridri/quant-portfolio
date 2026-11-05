"""Portfolio construction: backtest a custom allocation and search for the best one.

Pipeline
    1. Backtest the allocation you chose (fixed weights, daily returns).
    2. Read the correlation matrix: which holdings are the same bet?
    3. Maximise the Sharpe ratio (SciPy SLSQP, long only, capped weight per asset).
    4. Walk-forward test: every quarter, optimise on the previous two years only
       and hold those weights for the next quarter. The result never uses future
       data, unlike the Sharpe of the weights optimised on the full history.

Run in Spyder (F5) for a report on a sample portfolio.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .data import DataError, get_prices, perf_stats

TRADING_DAYS = 252
TRAIN_DAYS = 2 * TRADING_DAYS
STEP_DAYS = TRADING_DAYS // 4


def daily_returns(tickers, period: str = "5y") -> pd.DataFrame:
    return get_prices(tickers, period=period, min_obs=TRADING_DAYS).pct_change().dropna()


def _solve(objective, n: int, max_weight: float) -> np.ndarray:
    cap = max(max_weight, 1 / n)        # a cap below 1/n cannot sum to 100%
    res = minimize(objective, np.full(n, 1 / n), method="SLSQP", bounds=[(0, cap)] * n,
                   constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
                   options={"maxiter": 500, "ftol": 1e-9})
    w = np.clip(res.x, 0, None)
    return w / w.sum()


def max_sharpe(rets: pd.DataFrame, rf: float, max_weight: float) -> np.ndarray:
    mu, cov = rets.mean().values * TRADING_DAYS, rets.cov().values * TRADING_DAYS
    return _solve(lambda w: -(w @ mu - rf) / np.sqrt(w @ cov @ w), len(mu), max_weight)


def min_variance(rets: pd.DataFrame, max_weight: float) -> np.ndarray:
    cov = rets.cov().values * TRADING_DAYS
    return _solve(lambda w: w @ cov @ w, cov.shape[0], max_weight)


def walk_forward(rets: pd.DataFrame, optimiser) -> pd.Series:
    """Out-of-sample returns: `optimiser(past returns)` is refitted every quarter."""
    out = []
    for start in range(TRAIN_DAYS, len(rets), STEP_DAYS):
        w = optimiser(rets.iloc[start - TRAIN_DAYS:start])
        out.append(rets.iloc[start:start + STEP_DAYS] @ w)
    return pd.concat(out) if out else pd.Series(dtype=float)


def correlation_notes(rets: pd.DataFrame, weights: np.ndarray, threshold: float = 0.7) -> dict:
    corr = rets.corr()
    pairs = [(a, b, corr.loc[a, b]) for i, a in enumerate(corr.index) for b in corr.index[i + 1:]]
    vol = rets.std().values
    port_vol = np.sqrt(weights @ rets.cov().values @ weights)
    return {
        "corr": corr,
        "average": float(np.mean([p[2] for p in pairs])) if pairs else 0.0,
        "high": sorted([p for p in pairs if p[2] >= threshold], key=lambda p: -p[2]),
        "diversification_ratio": float((weights * vol).sum() / port_vol),
        "effective_positions": float(1 / (weights ** 2).sum()),
    }


def backtest(rets: pd.DataFrame, weights: np.ndarray, rf: float, benchmark: pd.Series | None = None) -> dict:
    r = rets @ weights
    out = {"returns": r, "stats": perf_stats(r, rf=rf)}
    if benchmark is not None:
        b = benchmark.reindex(r.index).fillna(0)
        out["benchmark"] = b
        out["benchmark_stats"] = perf_stats(b, rf=rf)
    return out


def optimise(rets: pd.DataFrame, current: np.ndarray, rf: float = 0.03, max_weight: float = 0.4) -> dict:
    if len(rets.columns) < 2:
        raise DataError("The optimiser needs at least two tickers.")
    n = len(rets.columns)
    best = max_sharpe(rets, rf, max_weight)
    safest = min_variance(rets, max_weight)

    # Same out-of-sample window for every candidate
    oos = {
        "Best Sharpe method": walk_forward(rets, lambda x: max_sharpe(x, rf, max_weight)),
        "Lowest risk method": walk_forward(rets, lambda x: min_variance(x, max_weight)),
    }
    window = next(iter(oos.values())).index
    enough_history = len(window) >= TRADING_DAYS // 2
    if enough_history:
        oos["Your allocation"] = rets.loc[window] @ current
        oos["Equal weights"] = rets.loc[window] @ np.full(n, 1 / n)

    return {
        "weights": pd.DataFrame({"Yours": current, "Max Sharpe": best, "Min variance": safest}, index=rets.columns),
        "in_sample": {name: perf_stats(rets @ w, rf=rf)
                      for name, w in [("Yours", current), ("Max Sharpe", best), ("Min variance", safest)]},
        "out_of_sample": {k: perf_stats(v, rf=rf) for k, v in oos.items()} if enough_history else {},
        "oos_curves": pd.DataFrame({k: (1 + v).cumprod() for k, v in oos.items()}) if enough_history else None,
        "oos_start": window[0] if enough_history else None,
    }


if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "JPM", "XOM", "JNJ", "GLD", "TLT"]
    rets = daily_returns(tickers)
    current = np.full(len(tickers), 1 / len(tickers))
    res = optimise(rets, current)
    print(res["weights"].round(3))
    print(pd.DataFrame(res["in_sample"]).T[["cagr", "volatility", "sharpe", "max_drawdown"]].round(3))
    print(pd.DataFrame(res["out_of_sample"]).T[["cagr", "volatility", "sharpe", "max_drawdown"]].round(3))
