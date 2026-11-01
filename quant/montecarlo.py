"""Project 1 - Monte Carlo portfolio risk: VaR & Expected Shortfall.

Pipeline
    1. Download >= 2 years of daily prices (yfinance), compute daily returns.
    2. Estimate mean, volatility and the correlation matrix.
    3. Simulate N correlated paths over the holding period. Correlation is
       embedded with a Cholesky factor L (C = L L'): eps = Z L'.
    4. VaR = loss at the (1 - alpha) percentile, ES = mean loss beyond VaR.
    5. Sensitivity: force a uniform pairwise correlation rho and watch VaR/ES
       react. Same random draws for every rho (common random numbers) so only
       the correlation changes.

Run in Spyder (F5) to print a full risk report.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import DataError, dates, get_prices, to_json_safe

DEFAULT_TICKERS = ["AAPL", "MSFT", "JPM", "XOM", "JNJ"]
TRADING_DAYS = 252


def nearest_correlation(c: np.ndarray) -> np.ndarray:
    """Clip negative eigenvalues so a user-modified matrix stays Cholesky-able."""
    vals, vecs = np.linalg.eigh((c + c.T) / 2)
    vals = np.clip(vals, 1e-8, None)
    c = vecs @ np.diag(vals) @ vecs.T
    d = np.sqrt(np.diag(c))
    return c / np.outer(d, d)


def simulate(mu: np.ndarray, sigma: np.ndarray, corr: np.ndarray, weights: np.ndarray,
             horizon: int, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Correlated daily log-returns -> portfolio return over the horizon.

    z has shape (n_sims, horizon, n_assets) of i.i.d. N(0, 1).
    Returns (portfolio horizon returns, portfolio cumulative path).
    """
    L = np.linalg.cholesky(corr)
    eps = z @ L.T                                    # correlated shocks
    log_r = (mu - 0.5 * sigma ** 2) + eps * sigma    # GBM daily log-returns
    growth = np.exp(np.cumsum(log_r, axis=1))        # (n_sims, horizon, n_assets)
    path = growth @ weights                          # buy & hold portfolio value / V0
    return path[:, -1] - 1, path


def var_es(returns: np.ndarray, alpha: float) -> tuple[float, float]:
    q = np.percentile(returns, (1 - alpha) * 100)
    tail = returns[returns <= q]
    return -q, -tail.mean()


def run(tickers=None, weights=None, period: str = "3y", horizon: int = 21,
        n_sims: int = 10_000, alpha: float = 0.95, notional: float = 1_000_000,
        seed: int = 42) -> dict:
    tickers = tickers or DEFAULT_TICKERS
    prices = get_prices(tickers, period=period, min_obs=400)
    tickers = list(prices.columns)
    n = len(tickers)
    if n < 2:
        raise DataError("A portfolio needs at least two assets.")
    if not 1 <= horizon <= 252:
        raise DataError("Horizon must be between 1 and 252 trading days.")
    n_sims = int(min(max(n_sims, 1000), 50_000))

    if weights is None:
        w = np.full(n, 1 / n)
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != n or w.sum() <= 0:
            raise DataError("Provide one positive weight per ticker.")
        w = w / w.sum()

    rets = np.log(prices).diff().dropna()
    mu = rets.mean().values
    sigma = rets.std().values
    corr = rets.corr().values

    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_sims, horizon, n))

    port_ret, path = simulate(mu, sigma, corr, w, horizon, z)
    var, es = var_es(port_ret, alpha)

    # Benchmarks: parametric (variance-covariance) and historical VaR
    from scipy.stats import norm
    cov = np.outer(sigma, sigma) * corr
    port_mu_d = w @ mu
    port_sig_d = np.sqrt(w @ cov @ w)
    z_a = norm.ppf(1 - alpha)
    param_var = -(port_mu_d * horizon + z_a * port_sig_d * np.sqrt(horizon))
    param_es = -(port_mu_d * horizon - port_sig_d * np.sqrt(horizon) * norm.pdf(z_a) / (1 - alpha))
    hist_h = (np.exp(rets.rolling(horizon).sum().dropna()) - 1).values @ w  # overlapping windows
    hist_var, hist_es = var_es(hist_h, alpha)

    # Diversification: what VaR would be if every asset were perfectly correlated
    standalone_sig = (w * sigma).sum()
    diversification_ratio = standalone_sig / port_sig_d

    # Sensitivity: uniform correlation rho, same random numbers
    avg_rho = corr[np.triu_indices(n, 1)].mean()
    rho_grid = sorted(set(np.round(np.r_[np.linspace(-0.2, 0.95, 24), avg_rho], 4)))
    min_rho = -1 / (n - 1) + 1e-3
    sens = []
    for rho in rho_grid:
        if rho <= min_rho:
            continue
        c = np.full((n, n), rho)
        np.fill_diagonal(c, 1.0)
        r_s, _ = simulate(mu, sigma, nearest_correlation(c), w, horizon, z)
        v, e = var_es(r_s, alpha)
        sens.append({"rho": float(rho), "var": v, "es": e, "is_current": bool(np.isclose(rho, round(avg_rho, 4)))})

    # Stress: blend the real matrix toward 1 (crisis correlations)
    stress = []
    for lam in [0, 0.25, 0.5, 0.75, 1.0]:
        c = nearest_correlation((1 - lam) * corr + lam * np.ones((n, n)))
        r_s, _ = simulate(mu, sigma, c, w, horizon, z)
        v, e = var_es(r_s, alpha)
        stress.append({"lambda": lam, "var": v, "es": e})

    # Fan chart percentiles and a handful of sample paths
    full = np.hstack([np.ones((n_sims, 1)), path])
    pct = {str(p): np.percentile(full, p, axis=0) for p in (1, 5, 25, 50, 75, 95, 99)}
    sample_idx = rng.choice(n_sims, size=min(120, n_sims), replace=False)

    hist_counts, edges = np.histogram(port_ret, bins=80)

    result = {
        "params": {"tickers": tickers, "weights": w, "period": period, "horizon": horizon,
                   "n_sims": n_sims, "alpha": alpha, "notional": notional,
                   "start": prices.index[0].strftime("%Y-%m-%d"),
                   "end": prices.index[-1].strftime("%Y-%m-%d"), "n_obs": len(rets)},
        "assets": [{"ticker": t, "weight": w[i], "ann_return": mu[i] * TRADING_DAYS,
                    "ann_vol": sigma[i] * np.sqrt(TRADING_DAYS)} for i, t in enumerate(tickers)],
        "corr": corr,
        "avg_corr": avg_rho,
        "risk": {
            "mc_var": var, "mc_es": es,
            "param_var": param_var, "param_es": param_es,
            "hist_var": hist_var, "hist_es": hist_es,
            "mc_var_cash": var * notional, "mc_es_cash": es * notional,
            "expected_return": port_ret.mean(), "prob_loss": (port_ret < 0).mean(),
            "port_ann_vol": port_sig_d * np.sqrt(TRADING_DAYS),
            "diversification_ratio": diversification_ratio,
            "worst": port_ret.min(), "best": port_ret.max(),
        },
        "distribution": {"counts": hist_counts, "edges": edges},
        "fan": {"days": list(range(horizon + 1)), "pct": pct,
                "samples": full[sample_idx]},
        "sensitivity": sens,
        "stress": stress,
        "history": {"dates": dates(prices.index),
                    "base100": {t: (prices[t] / prices[t].iloc[0] * 100).round(2).values for t in tickers}},
    }
    return to_json_safe(result)


if __name__ == "__main__":
    res = run()
    r, p = res["risk"], res["params"]
    print(f"\nPortfolio {', '.join(p['tickers'])}  |  {p['start']} -> {p['end']}")
    print(f"{p['n_sims']:,} simulations, {p['horizon']}-day horizon, {p['alpha']:.0%} confidence\n")
    print(pd.DataFrame(res["assets"]).set_index("ticker").round(4))
    print(f"\nMonte Carlo VaR : {r['mc_var']:.2%}  (${r['mc_var_cash']:,.0f})")
    print(f"Monte Carlo ES  : {r['mc_es']:.2%}  (${r['mc_es_cash']:,.0f})")
    print(f"Parametric VaR  : {r['param_var']:.2%}   Historical VaR: {r['hist_var']:.2%}")
    print(f"Diversification ratio: {r['diversification_ratio']:.2f}")
    print("\nCorrelation sensitivity")
    print(pd.DataFrame(res["sensitivity"]).round(4).to_string(index=False))
