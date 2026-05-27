# tools/dashboard.py

A single-file Plotly Dash log viewer for IMC Prosperity backtester output and the JSON `.log` exports from the Prosperity website. **883 lines, zero build step.**

## What it renders

For any input it auto-detects, the dashboard shows:

- **Per-product PnL curves** — realised + unrealised, with day-boundary separators when the source spans multiple days
- **Order book reconstruction at the active tick** — three-level book with our own orders highlighted in amber
- **Position trajectories** — per-product position vs time, with the position-limit lines drawn in
- **Mid-price and micro-price curves** with our trade markers overlaid
- **Market vs own trade volume bars** for sanity-checking fill rates

The colour palette matches the dark GitHub theme (`#0d1117` background, `#e6edf3` text, blue/red bid/ask).

## Two input modes

**1. JSON log mode — a single `.log` file**

```bash
python tools/dashboard.py path/to/submission.log
```

Accepts both backtester output (`prosperity4btest cli round_5/algorithmic/trader.py 4 > out.log`) and live Prosperity-website downloads. We used this mode throughout the campaign to do post-mortem on every submission.

**2. CSV mode — multiple `prices_*.csv` + `trades_*.csv` files stitched together**

```bash
python tools/dashboard.py prices_*.csv trades_*.csv
```

Stitches multi-day historical data so a single dashboard view spans (e.g.) day 2 + day 3 + day 4 with the day boundaries drawn in. We used this mode for cross-day regime checks and for the worst-day-mode rule (eyeballing whether the worst single day was positive before we shipped a candidate).

**3. No arguments — file picker in the browser**

```bash
python tools/dashboard.py
```

Drops you on a landing page with a drag-and-drop file picker. Useful when iterating on multiple candidate `.log` files in parallel.

## Running it

```bash
pip install dash plotly pandas numpy
python tools/dashboard.py path/to/file.log
# Then open http://127.0.0.1:8050
```

`uv` users:

```bash
uv run tools/dashboard.py path/to/file.log
```

## Why a Python single-file tool

The Prosperity ecosystem already has the excellent [`jmerle/imc-prosperity-3-visualizer`](https://github.com/jmerle/imc-prosperity-3-visualizer) for browser-based playback, and the hosted [Equirag visualizer](https://prosperity.equirag.com/) for sharing without local install. Our dashboard is intentionally simpler and slower: a single Python file with no build step, designed to be edited and re-run during a debugging session — *we treated it as part of the trader's source code*, not as third-party infrastructure.

The most useful single feature, in retrospect: a per-product PnL attribution overlay that surfaces which product is contributing to a strategy's PnL on a given tick. The Round 5 `OXYGEN_SHAKE_CHOCOLATE` carry was visible in the dashboard's per-product panel several backtest days before we sized into it on the live tape.
