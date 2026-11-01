"""Pre-compute JSON snapshots into site/data so the website also works without
a Python server (e.g. on GitHub Pages). The live API is used whenever
app.py is running; these files are the fallback.

    python build_static.py
"""
import json
import sys
from pathlib import Path

from quant import montecarlo, pairs, sma

OUT = Path(__file__).resolve().parent / "site" / "data"
PAIRS = [("V", "MA"), ("EWA", "EWC"), ("KO", "PEP"), ("SPY", "IVV"), ("XOM", "CVX"), ("GS", "MS")]
SMA = ["SPY", "QQQ", "AAPL", "GLD"]


def save(name, build):
    """Refresh one snapshot; on a data error keep the previous file instead of failing the deploy."""
    try:
        payload = build()
    except Exception as e:
        print(f"  kept previous {name}: {e}", file=sys.stderr)
        return False
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(payload, separators=(",", ":")))
    print("  wrote", name)
    return True


if __name__ == "__main__":
    jobs = [("montecarlo", montecarlo.run)]
    jobs += [(f"pairs_{a}_{b}", lambda a=a, b=b: pairs.run(a, b)) for a, b in PAIRS]
    jobs += [(f"sma_{t}", lambda t=t: sma.run(t)) for t in SMA]
    ok = sum(save(name, build) for name, build in jobs)
    print(f"{ok}/{len(jobs)} snapshots refreshed")
    sys.exit(0 if ok else 1)
