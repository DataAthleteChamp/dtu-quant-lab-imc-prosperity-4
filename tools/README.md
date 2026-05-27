# tools/dashboard.py

A single-file Plotly Dash log viewer for IMC Prosperity backtester output.

## What it shows

For any `.log` file produced by the official `prosperity4btest` backtester or by the live Prosperity website, the dashboard renders:

- Per-product PnL curves
- Order book reconstructions at each tick
- Position trajectories
- Realised vs unrealised PnL splits
- Trade markers overlaid on mid-price curves

Both backtester output and Prosperity-website JSON tape formats are auto-detected from the input file.

## Running it

```bash
pip install dash plotly pandas
python tools/dashboard.py path/to/file.log
```

The dashboard runs locally at `http://127.0.0.1:8050`.

## Why a Python single-file tool

The Prosperity ecosystem already has the excellent [`jmerle/imc-prosperity-3-visualizer`](https://github.com/jmerle/imc-prosperity-3-visualizer) for browser-based playback. Our dashboard is intentionally simpler: a single Python file with no build step, intended to be edited and re-run during a debugging session.
