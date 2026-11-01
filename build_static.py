"""Pre-compute JSON results into site/data so the website works on its own
(GitHub Pages, no Python server). Runs every weekday in GitHub Actions.

    python build_static.py

The site offers these tickers in its lists. Any other ticker needs app.py
running locally (Spyder: open app.py, F5).
"""
import json
import sys
from itertools import combinations
from pathlib import Path

import pandas as pd

from quant import montecarlo, pairs, sma
from quant.data import get_ohlc

OUT = Path(__file__).resolve().parent / "site" / "data"

PAIR_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD",      # tech
    "JPM", "BAC", "GS", "MS", "V", "MA",                 # financials
    "KO", "PEP", "PG", "XOM", "CVX", "HD", "LOW", "UPS", "FDX",
    "SPY", "IVV", "QQQ", "GLD", "GDX", "EWA", "EWC",     # ETFs
]
SMA_UNIVERSE = PAIR_UNIVERSE + ["AMZN", "TSLA", "TLT", "^FCHI", "^GSPC", "MC.PA", "TTE.PA", "AIR.PA",
                                "BTC-USD", "ETH-USD"]
MC_PRESETS = {
    "Diversified US": ["AAPL", "MSFT", "JPM", "XOM", "JNJ"],
    "Semiconductors": ["NVDA", "AMD", "AVGO", "TSM"],
    "60/40 + gold": ["SPY", "TLT", "GLD"],
    "CAC 40": ["MC.PA", "OR.PA", "TTE.PA", "SAN.PA", "AIR.PA"],
}


def fname(*tickers):
    """Must match snapName() in site/assets/app.js."""
    return "_".join(t.replace("^", "-") for t in tickers)


def save(name, build):
    """Write one result; on a data error keep the previous file instead of failing the deploy."""
    try:
        payload = build()
    except Exception as e:
        print(f"  skipped {name}: {e}", file=sys.stderr)
        return False
    (OUT / f"{name}.json").write_text(json.dumps(payload, separators=(",", ":")))
    return True


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    ok_mc = {k: v for k, v in MC_PRESETS.items() if save(f"mc_{fname(*v)}", lambda v=v: montecarlo.run(v))}
    print(f"Monte Carlo: {len(ok_mc)}/{len(MC_PRESETS)}")

    ok_sma = [t for t in SMA_UNIVERSE if save(f"sma_{fname(t)}", lambda t=t: sma.run(t))]
    print(f"SMA: {len(ok_sma)}/{len(SMA_UNIVERSE)}")

    # One download per ticker (cached, shared with the SMA step), then every pair
    closes = pd.concat({t: get_ohlc(t, "max")["Close"] for t in PAIR_UNIVERSE if t in ok_sma}, axis=1)
    ok_pairs = [t for t in PAIR_UNIVERSE if t in closes.columns]
    n = 0
    for a, b in combinations(sorted(ok_pairs), 2):
        n += save(f"pairs_{fname(a, b)}", lambda a=a, b=b: pairs.run(a, b, closes=closes))
    print(f"Pairs: {n}/{len(ok_pairs) * (len(ok_pairs) - 1) // 2}")

    universe = {"as_of": closes.index[-1].strftime("%Y-%m-%d"), "pairs": sorted(ok_pairs),
                "sma": ok_sma, "mc": ok_mc}
    (OUT / "universe.json").write_text(json.dumps(universe, separators=(",", ":")))
    sys.exit(0 if ok_sma else 1)
