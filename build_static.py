"""Pre-compute JSON snapshots into site/data so the website also works without
a Python server (e.g. on GitHub Pages). The live API is used whenever
app.py is running; these files are the fallback.

    python build_static.py
"""
import json
from pathlib import Path

from quant import montecarlo, pairs, sma

OUT = Path(__file__).resolve().parent / "site" / "data"
PAIRS = [("V", "MA"), ("EWA", "EWC"), ("KO", "PEP"), ("SPY", "IVV"), ("XOM", "CVX"), ("GS", "MS")]
SMA = ["SPY", "QQQ", "AAPL", "GLD"]


def save(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(payload, separators=(",", ":")))
    print("  wrote", name)


if __name__ == "__main__":
    save("montecarlo", montecarlo.run())
    for a, b in PAIRS:
        save(f"pairs_{a}_{b}", pairs.run(a, b))
    for t in SMA:
        save(f"sma_{t}", sma.run(t))
