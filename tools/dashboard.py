"""
Prosperity 4 Trading Dashboard
================================
Supports two data modes:
  1. JSON log  — single .log file from Prosperity simulator
  2. CSV mode  — multiple prices_*.csv + trades_*.csv files (multi-day, stitched together)

Usage:
    uv run dashboard.py [path/to/file.log]
    uv run dashboard.py prices_*.csv trades_*.csv
    uv run dashboard.py                     # file picker in browser
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, State, ctx
import base64

# ─────────────────────────── colour palette ───────────────────────────────
BG         = "#0d1117"
PANEL_BG   = "#161b22"
BORDER     = "#30363d"
TEXT       = "#e6edf3"
TEXT_DIM   = "#8b949e"
BID_COL    = "#388bfd"
ASK_COL    = "#f85149"
OWN_COL    = "#ffa657"
MARKET_COL = "#3fb950"
ACCENT     = "#58a6ff"
PNL_COL    = "#a371f7"
POS_COL    = "#ffa657"

DAY_SPAN   = 1_000_000   # timestamp units per day

# ══════════════════════════════════════════════════════════════════════════
#  PARSING
# ══════════════════════════════════════════════════════════════════════════

def _day_from_filename(name: str) -> int | None:
    m = re.search(r"day_(-?\d+)", name)
    return int(m.group(1)) if m else None

def _offset_for_day(day: int, all_days: list[int]) -> int:
    idx = sorted(all_days).index(day)
    return idx * DAY_SPAN

def parse_json_log(raw: str | bytes) -> dict:
    """Parse the official Prosperity website log format (single JSON blob)."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)

    activities = pd.read_csv(io.StringIO(data["activitiesLog"]), sep=";")
    activities["timestamp"] = activities["timestamp"].astype(int)

    trade_rows = data.get("tradeHistory", [])
    trades = pd.DataFrame(trade_rows) if trade_rows else pd.DataFrame(
        columns=["timestamp","buyer","seller","symbol","price","quantity"])
    if not trades.empty:
        trades["timestamp"] = trades["timestamp"].astype(int)
        def classify(row):
            if row["buyer"] == "SUBMISSION":  return "our_buy"
            if row["seller"] == "SUBMISSION": return "our_sell"
            return "market"
        trades["trade_type"] = trades.apply(classify, axis=1)
        trades.rename(columns={"symbol": "product"}, inplace=True)

    logs_raw = data.get("logs", [])
    logs = pd.DataFrame(logs_raw) if logs_raw else pd.DataFrame(
        columns=["timestamp","sandboxLog","lambdaLog"])
    if not logs.empty:
        logs["timestamp"] = logs["timestamp"].astype(int)

    activities["global_ts"] = activities["timestamp"]
    if not trades.empty:
        trades["global_ts"] = trades["timestamp"]

    days = sorted(activities["day"].unique().tolist())
    products = sorted(activities["product"].unique().tolist())

    return dict(activities=activities, trades=trades, logs=logs,
                products=products, days=days, day_boundaries=[], mode="log")


def parse_backtester_log(raw: str | bytes) -> dict:
    """Parse the jmerle/nabayansaha backtester log format.

    Format:
        Sandbox logs:
        {"sandboxLog": "", "lambdaLog": "", "timestamp": 0}
        ...

        Activities log:
        day;timestamp;product;bid_price_1;...;profit_and_loss
        -2;0;EMERALDS;...

        Trade History:
        [{"timestamp": 900, "buyer": "", "seller": "SUBMISSION", ...}]
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")

    sections: dict[str, str] = {}
    current_key = None
    buf: list[str] = []

    for line in raw.splitlines():
        stripped = line.rstrip()
        if stripped == "Sandbox logs:":
            if current_key:
                sections[current_key] = "\n".join(buf)
            current_key, buf = "sandbox", []
        elif stripped == "Activities log:":
            if current_key:
                sections[current_key] = "\n".join(buf)
            current_key, buf = "activities", []
        elif stripped == "Trade History:":
            if current_key:
                sections[current_key] = "\n".join(buf)
            current_key, buf = "trades", []
        elif current_key is not None:
            buf.append(stripped)

    if current_key:
        sections[current_key] = "\n".join(buf)

    # ── sandbox / algo logs ───────────────────────────────────────────────
    log_rows = []
    for line in sections.get("sandbox", "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            log_rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    logs = (pd.DataFrame(log_rows, columns=["timestamp", "sandboxLog", "lambdaLog"])
            if log_rows else
            pd.DataFrame(columns=["timestamp", "sandboxLog", "lambdaLog"]))
    if not logs.empty:
        logs["timestamp"] = logs["timestamp"].astype(int)

    # ── activities (already semicolon CSV with a day column) ──────────────
    act_text = sections.get("activities", "").strip()
    if not act_text:
        raise ValueError("No 'Activities log:' section found in backtester log.")
    activities = pd.read_csv(io.StringIO(act_text), sep=";")
    activities["timestamp"] = activities["timestamp"].astype(int)

    all_days = sorted(activities["day"].unique().tolist())
    activities["global_ts"] = activities.apply(
        lambda r: int(r["timestamp"]) + _offset_for_day(int(r["day"]), all_days), axis=1)

    # ── trade history (JSON array, may have trailing commas) ──────────────
    trade_text = sections.get("trades", "").strip()
    trades = pd.DataFrame(
        columns=["timestamp", "global_ts", "buyer", "seller",
                 "product", "price", "quantity", "trade_type"])

    if trade_text:
        # strip trailing commas before } or ] to handle Python-style JSON
        clean = re.sub(r",\s*([}\]])", r"\1", trade_text)
        try:
            trade_rows = json.loads(clean)
        except json.JSONDecodeError:
            trade_rows = []

        if trade_rows:
            trades = pd.DataFrame(trade_rows)
            trades["timestamp"] = trades["timestamp"].astype(int)
            trades.rename(columns={"symbol": "product"}, inplace=True, errors="ignore")

            def classify(row):
                if row.get("buyer") == "SUBMISSION":  return "our_buy"
                if row.get("seller") == "SUBMISSION": return "our_sell"
                return "market"
            trades["trade_type"] = trades.apply(classify, axis=1)

            # map each trade timestamp to its day via nearest activities row
            _ts_arr = (activities[["timestamp", "day"]]
                       .drop_duplicates("timestamp")
                       .sort_values("timestamp"))
            _ts_vals = _ts_arr["timestamp"].to_numpy()
            _day_vals = _ts_arr["day"].to_numpy()
            def _trade_day(ts):
                idx = int(abs(_ts_vals - ts).argmin())
                return int(_day_vals[idx])

            trades["day"] = trades["timestamp"].apply(_trade_day)
            trades["global_ts"] = trades.apply(
                lambda r: int(r["timestamp"]) + _offset_for_day(int(r["day"]), all_days),
                axis=1)

    day_boundaries = [_offset_for_day(d, all_days) for d in all_days[1:]]
    products = sorted(activities["product"].unique().tolist())

    return dict(activities=activities, trades=trades, logs=logs,
                products=products, days=all_days,
                day_boundaries=day_boundaries, mode="backtester")


def parse_log(raw: str | bytes) -> dict:
    """Auto-detect log format and dispatch to the right parser."""
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    if text.lstrip().startswith("{") or text.lstrip().startswith("["):
        return parse_json_log(text)
    if "Sandbox logs:" in text:
        return parse_backtester_log(text)
    raise ValueError(
        "Unrecognised log format — expected official Prosperity JSON log "
        "or backtester log with 'Sandbox logs:' / 'Activities log:' sections."
    )


def parse_csv_files(files: list[tuple[str, bytes]]) -> dict:
    price_files = [(n, c) for n, c in files if "price" in n.lower()]
    trade_files = [(n, c) for n, c in files if "trade" in n.lower()]

    # ── prices ────────────────────────────────────────────────────────────
    price_dfs = []
    for name, content in price_files:
        day = _day_from_filename(name)
        df = pd.read_csv(io.BytesIO(content), sep=";")
        df["timestamp"] = df["timestamp"].astype(int)
        if day is None and "day" in df.columns:
            day = int(df["day"].iloc[0])
        if day is not None:
            df["day"] = day
        price_dfs.append(df)

    if not price_dfs:
        raise ValueError("No price files found.")

    all_price_days = sorted({int(df["day"].iloc[0]) for df in price_dfs})
    for df in price_dfs:
        day = int(df["day"].iloc[0])
        df["global_ts"] = df["timestamp"] + _offset_for_day(day, all_price_days)

    activities = pd.concat(price_dfs, ignore_index=True).sort_values("global_ts")

    # ── trades ────────────────────────────────────────────────────────────
    trade_dfs = []
    for name, content in trade_files:
        day = _day_from_filename(name)
        df = pd.read_csv(io.BytesIO(content), sep=";")
        df["timestamp"] = df["timestamp"].astype(int)
        if day is None and "day" in df.columns:
            day = int(df["day"].iloc[0])
        if day is not None:
            df["day"] = day
        trade_dfs.append(df)

    if trade_dfs:
        all_trade_days = sorted({int(df["day"].iloc[0]) for df in trade_dfs})
        for df in trade_dfs:
            day = int(df["day"].iloc[0])
            df["global_ts"] = df["timestamp"] + _offset_for_day(day, all_trade_days)
        trades = pd.concat(trade_dfs, ignore_index=True).sort_values("global_ts")
        trades.rename(columns={"symbol": "product"}, inplace=True, errors="ignore")
        trades["trade_type"] = "market"
        trades["buyer"]  = trades["buyer"].fillna("").astype(str)
        trades["seller"] = trades["seller"].fillna("").astype(str)
    else:
        trades = pd.DataFrame(
            columns=["timestamp","global_ts","product","buyer","seller",
                     "price","quantity","trade_type"])

    day_boundaries = [_offset_for_day(d, all_price_days) for d in all_price_days[1:]]
    products = sorted(activities["product"].unique().tolist())
    logs = pd.DataFrame(columns=["timestamp","sandboxLog","lambdaLog"])

    return dict(activities=activities, trades=trades, logs=logs,
                products=products, days=all_price_days,
                day_boundaries=day_boundaries, mode="csv")


# ══════════════════════════════════════════════════════════════════════════
#  FIGURE BUILDERS
# ══════════════════════════════════════════════════════════════════════════

def _vol_to_size(vol: pd.Series, min_s=4, max_s=22) -> pd.Series:
    v = vol.fillna(0).clip(lower=0)
    if v.max() == 0:
        return pd.Series(min_s, index=vol.index)
    return (v / v.max() * (max_s - min_s) + min_s)

def _day_boundary_shapes(boundaries: list[int]) -> list[dict]:
    return [dict(type="line", xref="x", yref="paper",
                 x0=b, x1=b, y0=0, y1=1,
                 line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dash"))
            for b in boundaries]

def _day_annotations(boundaries: list[int], days: list[int], x_min: float) -> list[dict]:
    sorted_days = sorted(days)
    anns = []
    # first day label at leftmost point
    anns.append(dict(
        xref="x", yref="paper", x=x_min + 5000, y=0.99,
        text=f"Day {sorted_days[0]}", showarrow=False,
        font=dict(color="rgba(255,255,255,0.35)", size=10, family="monospace"),
        xanchor="left", yanchor="top",
    ))
    for i, b in enumerate(boundaries):
        if i + 1 < len(sorted_days):
            anns.append(dict(
                xref="x", yref="paper", x=b + 5000, y=0.99,
                text=f"Day {sorted_days[i+1]}", showarrow=False,
                font=dict(color="rgba(255,255,255,0.35)", size=10, family="monospace"),
                xanchor="left", yanchor="top",
            ))
    return anns

def _empty_fig(height=150):
    fig = go.Figure()
    fig.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                      font=dict(color=TEXT, family="monospace"),
                      margin=dict(l=60, r=20, t=10, b=30), height=height)
    return fig

def build_main_figure(
    activities, trades, product,
    day_filter="all", show_bids=True, show_asks=True,
    show_own=True, show_market=True,
    norm_col=None, min_qty=0, max_qty=9999,
    day_boundaries=None, days=None,
) -> go.Figure:

    act = activities[activities["product"] == product].copy()
    if day_filter != "all":
        act = act[act["day"] == int(day_filter)]
    tr = trades[trades["product"] == product].copy() if not trades.empty else pd.DataFrame()
    if day_filter != "all" and not tr.empty and "day" in tr.columns:
        tr = tr[tr["day"] == int(day_filter)]

    if act.empty:
        return _empty_fig(440)

    x_col = "global_ts"

    # normalisation
    if norm_col and norm_col in act.columns and not act[norm_col].isna().all():
        ref = act.set_index(x_col)[norm_col]
        def norm_fn(xs, prices):
            return prices - ref.reindex(xs).values
    else:
        norm_fn = None

    fig = go.Figure()

    for side in ("bid", "ask"):
        if side == "bid" and not show_bids: continue
        if side == "ask" and not show_asks: continue
        col = BID_COL if side == "bid" else ASK_COL
        r, g, b = int(col[1:3],16), int(col[3:5],16), int(col[5:7],16)

        for i in range(1, 4):
            pc, vc = f"{side}_price_{i}", f"{side}_volume_{i}"
            mask = act[pc].notna() & act[vc].notna()
            sub  = act[mask]
            if sub.empty: continue
            prices = sub[pc].values
            if norm_fn: prices = norm_fn(sub[x_col].values, prices)
            alpha = 1.0 - (i-1) * 0.25
            label = f"{'Bid' if side=='bid' else 'Ask'} L{i}"
            fig.add_trace(go.Scatter(
                x=sub[x_col], y=prices, mode="markers",
                marker=dict(symbol="circle", size=_vol_to_size(sub[vc]),
                            color=f"rgba({r},{g},{b},{alpha:.2f})", line=dict(width=0)),
                name=label, legendgroup=f"{side}_levels",
                legendgrouptitle_text=("Bids" if i==1 and side=="bid" else
                                       "Asks" if i==1 and side=="ask" else None),
                hovertemplate=f"<b>{label}</b><br>ts: %{{x}}<br>price: %{{y}}<br>vol: %{{customdata}}<extra></extra>",
                customdata=sub[vc],
            ))

    if not tr.empty:
        tr_f = tr[(tr["quantity"] >= min_qty) & (tr["quantity"] <= max_qty)].copy()
        if norm_fn and not tr_f.empty:
            ref2 = act.set_index(x_col)["mid_price"]
            def nref(t):
                idx = max(ref2.index.searchsorted(t, side="right") - 1, 0)
                return ref2.iloc[idx] if len(ref2) else 0
            tr_f["price_plot"] = tr_f["price"] - tr_f[x_col].map(nref)
        else:
            tr_f["price_plot"] = tr_f["price"]

        for ttype, sym, col, name, show in [
            ("market",   "circle", MARKET_COL, "Market trade", show_market),
            ("our_buy",  "cross",  OWN_COL,    "Our buy",      show_own),
            ("our_sell", "x",      OWN_COL,    "Our sell",     show_own),
        ]:
            if not show: continue
            sub = tr_f[tr_f["trade_type"] == ttype]
            if sub.empty: continue
            fig.add_trace(go.Scatter(
                x=sub[x_col], y=sub["price_plot"], mode="markers",
                marker=dict(symbol=sym, size=_vol_to_size(sub["quantity"], 8, 20),
                            color=col, line=dict(width=1.5, color=col)),
                name=name, legendgroup="trades",
                legendgrouptitle_text="Trades" if ttype=="market" else None,
                hovertemplate=f"<b>{name}</b><br>ts: %{{x}}<br>price: %{{y}}<br>qty: %{{customdata}}<extra></extra>",
                customdata=sub["quantity"],
            ))

    if "mid_price" in act.columns:
        mp = act["mid_price"].values
        if norm_fn: mp = norm_fn(act[x_col].values, mp)
        fig.add_trace(go.Scatter(
            x=act[x_col], y=mp, mode="lines",
            line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"),
            name="Mid price", hoverinfo="skip",
        ))

    shapes = _day_boundary_shapes(day_boundaries or [])
    anns   = _day_annotations(day_boundaries or [], days or [],
                               act[x_col].min() if not act.empty else 0)

    fig.update_layout(
        plot_bgcolor=BG, paper_bgcolor=BG,
        font=dict(color=TEXT, family="monospace"),
        xaxis=dict(title="Global timestamp", showgrid=True, gridcolor=BORDER,
                   zeroline=False, tickfont=dict(size=11)),
        yaxis=dict(title="Δ from "+norm_col if norm_fn else "Price",
                   showgrid=True, gridcolor=BORDER, zeroline=False, tickfont=dict(size=11)),
        legend=dict(bgcolor=PANEL_BG, bordercolor=BORDER, borderwidth=1,
                    font=dict(size=11), groupclick="toggleitem"),
        shapes=shapes, annotations=anns,
        hovermode="x unified",
        margin=dict(l=60, r=20, t=10, b=40), height=440,
    )
    return fig


def build_pnl_figure(activities, product, day_filter, day_boundaries=None, days=None):
    act = activities[activities["product"] == product].copy()
    if day_filter != "all" and "day" in act.columns:
        act = act[act["day"] == int(day_filter)]
    if act.empty or "profit_and_loss" not in act.columns:
        return _empty_fig(150)
    fig = go.Figure(go.Scatter(
        x=act["global_ts"], y=act["profit_and_loss"],
        mode="lines", fill="tozeroy",
        line=dict(color=PNL_COL, width=1.5), fillcolor="rgba(163,113,247,0.15)",
        hovertemplate="ts: %{x}<br>PnL: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor=BG, paper_bgcolor=BG, font=dict(color=TEXT, family="monospace"),
        xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(title="PnL", showgrid=True, gridcolor=BORDER,
                   zeroline=True, zerolinecolor="rgba(255,255,255,0.3)", tickfont=dict(size=10)),
        shapes=_day_boundary_shapes(day_boundaries or []),
        margin=dict(l=60, r=20, t=10, b=30), height=150,
        showlegend=False, hovermode="x unified",
    )
    return fig


def build_position_figure(trades, product, day_filter, day_boundaries=None):
    tr = trades[trades["product"] == product].copy() if not trades.empty else pd.DataFrame()
    if day_filter != "all" and not tr.empty and "day" in tr.columns:
        tr = tr[tr["day"] == int(day_filter)]
    our = tr[tr["trade_type"].isin(["our_buy","our_sell"])].sort_values("global_ts") \
          if not tr.empty and "trade_type" in tr.columns else pd.DataFrame()
    if our.empty:
        return _empty_fig(150)
    our = our.copy()
    our["signed_qty"] = our.apply(
        lambda r: r["quantity"] if r["trade_type"]=="our_buy" else -r["quantity"], axis=1)
    our["position"] = our["signed_qty"].cumsum()
    colors = [POS_COL if v >= 0 else ASK_COL for v in our["position"]]
    fig = go.Figure(go.Scatter(
        x=our["global_ts"], y=our["position"],
        mode="lines+markers",
        line=dict(color=POS_COL, width=1.5, shape="hv"),
        marker=dict(color=colors, size=5),
        fill="tozeroy", fillcolor="rgba(255,166,87,0.12)",
        hovertemplate="ts: %{x}<br>pos: %{y}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor=BG, paper_bgcolor=BG, font=dict(color=TEXT, family="monospace"),
        xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(title="Position", showgrid=True, gridcolor=BORDER,
                   zeroline=True, zerolinecolor="rgba(255,255,255,0.3)", tickfont=dict(size=10)),
        shapes=_day_boundary_shapes(day_boundaries or []),
        margin=dict(l=60, r=20, t=10, b=30), height=150,
        showlegend=False, hovermode="x unified",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════
#  LAYOUT HELPERS
# ══════════════════════════════════════════════════════════════════════════

def card(children, style=None):
    base = dict(background=PANEL_BG, border=f"1px solid {BORDER}",
                borderRadius="8px", padding="12px")
    if style: base.update(style)
    return html.Div(children, style=base)

def section_label(text):
    return html.Div(text, style=dict(
        color=TEXT_DIM, fontSize="11px", fontWeight="600",
        letterSpacing="0.08em", textTransform="uppercase",
        marginBottom="6px", fontFamily="monospace"))

def _btn_style(active):
    return dict(
        background=ACCENT if active else BORDER,
        color=BG if active else TEXT_DIM,
        border="none", borderRadius="4px",
        padding="4px 10px", fontSize="11px", fontFamily="monospace",
        cursor="pointer", marginRight="4px", marginBottom="4px", fontWeight="600")

def toggle_btn(btn_id, label):
    return html.Button(label, id=btn_id, n_clicks=0, style=_btn_style(True))


# ══════════════════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════════════════

def create_app(initial_paths: list[str] | None = None) -> dash.Dash:
    app = dash.Dash(__name__, title="Prosperity 4 Dashboard",
                    suppress_callback_exceptions=True)

    app.layout = html.Div([
        dcc.Store(id="store-data"),
        dcc.Store(id="store-toggles", data=dict(bids=True, asks=True, own=True, market=True)),

        html.Div([
            html.Span("⬡ PROSPERITY 4", style=dict(
                color=ACCENT, fontWeight="700", fontSize="18px",
                fontFamily="monospace", letterSpacing="0.1em")),
            html.Span(" DASHBOARD", style=dict(
                color=TEXT_DIM, fontWeight="400", fontSize="18px", fontFamily="monospace")),
        ], style=dict(background=PANEL_BG, borderBottom=f"1px solid {BORDER}",
                      padding="12px 20px", display="flex", alignItems="center")),

        html.Div([

            # SIDEBAR
            html.Div([
                card([
                    section_label("Load files"),
                    dcc.Upload(
                        id="upload-files",
                        children=html.Div([
                            html.Div("📂 Drop files here or click", style=dict(color=TEXT_DIM, fontSize="12px")),
                            html.Div("prices_*.csv  trades_*.csv  *.log",
                                     style=dict(color=ACCENT, fontSize="11px",
                                                fontFamily="monospace", marginTop="4px")),
                            html.Div("(select multiple)", style=dict(color=TEXT_DIM, fontSize="10px", marginTop="2px")),
                        ]),
                        style=dict(border=f"1px dashed {BORDER}", borderRadius="6px",
                                   padding="12px", textAlign="center", cursor="pointer", background=BG),
                        multiple=True,
                    ),
                    html.Div(id="upload-status", style=dict(
                        color=TEXT_DIM, fontSize="11px", marginTop="6px", fontFamily="monospace")),
                ], style=dict(marginBottom="10px")),

                card([
                    section_label("Product"),
                    dcc.Dropdown(id="dd-product", options=[], value=None, className="dark-dd"),
                    html.Div(style=dict(height="10px")),
                    section_label("Day"),
                    dcc.Dropdown(id="dd-day",
                                 options=[{"label":"All days (stitched)","value":"all"}],
                                 value="all", className="dark-dd"),
                    html.Div(style=dict(height="10px")),
                    section_label("Normalise by"),
                    dcc.Dropdown(id="dd-norm",
                                 options=[{"label":"None","value":"none"}],
                                 value="none", className="dark-dd"),
                ], style=dict(marginBottom="10px")),

                card([
                    section_label("Order book"),
                    html.Div([toggle_btn("btn-bids","Bids"), toggle_btn("btn-asks","Asks")]),
                    html.Div(style=dict(height="8px")),
                    section_label("Trades"),
                    html.Div([toggle_btn("btn-own","Our trades"), toggle_btn("btn-market","Market")]),
                    html.Div(style=dict(height="8px")),
                    section_label("Qty filter"),
                    dcc.RangeSlider(id="qty-slider", min=0, max=100, step=1, value=[0,100],
                                    marks={0:"0",50:"50",100:"100"},
                                    tooltip={"placement":"bottom","always_visible":False}),
                ], style=dict(marginBottom="10px")),

                card([
                    section_label("Stats"),
                    html.Div(id="stats-panel", style=dict(
                        fontFamily="monospace", fontSize="12px", color=TEXT, lineHeight="1.8")),
                ]),
            ], style=dict(width="220px", flexShrink="0", padding="10px 0 10px 10px")),

            # MAIN AREA
            html.Div([
                card([
                    html.Div([
                        html.Span("Order Book", style=dict(
                            color=TEXT, fontFamily="monospace", fontSize="13px", fontWeight="600")),
                        html.Span(id="chart-subtitle", style=dict(
                            color=TEXT_DIM, fontFamily="monospace", fontSize="11px", marginLeft="10px")),
                    ], style=dict(marginBottom="6px")),
                    dcc.Graph(id="main-chart", figure=_empty_fig(440),
                              config=dict(displayModeBar=True, scrollZoom=True,
                                          modeBarButtonsToRemove=["select2d","lasso2d"],
                                          displaylogo=False)),
                ], style=dict(marginBottom="8px")),

                html.Div([
                    html.Div([card([section_label("PnL"),
                        dcc.Graph(id="pnl-chart", figure=_empty_fig(150),
                                  config=dict(displayModeBar=False))])],
                             style=dict(flex="1", marginRight="8px")),
                    html.Div([card([section_label("Position"),
                        dcc.Graph(id="pos-chart", figure=_empty_fig(150),
                                  config=dict(displayModeBar=False))])],
                             style=dict(flex="1")),
                ], style=dict(display="flex", marginBottom="8px")),

                card([
                    html.Div([
                        section_label("Algorithm log viewer"),
                        html.Span(id="log-ts-label", style=dict(
                            color=ACCENT, fontFamily="monospace", fontSize="11px", marginLeft="8px")),
                    ], style=dict(display="flex", alignItems="center", marginBottom="6px")),
                    html.Div([
                        html.Div([
                            html.Div("SANDBOX", style=dict(color=TEXT_DIM, fontSize="10px",
                                fontFamily="monospace", marginBottom="4px", fontWeight="600")),
                            html.Pre(id="log-sandbox", children="— no log —", style=dict(
                                color=TEXT, fontFamily="monospace", fontSize="11px",
                                background=BG, padding="8px", borderRadius="4px",
                                maxHeight="100px", overflow="auto", margin="0",
                                whiteSpace="pre-wrap", border=f"1px solid {BORDER}")),
                        ], style=dict(flex="1", marginRight="8px")),
                        html.Div([
                            html.Div("LAMBDA", style=dict(color=TEXT_DIM, fontSize="10px",
                                fontFamily="monospace", marginBottom="4px", fontWeight="600")),
                            html.Pre(id="log-lambda", children="— no log —", style=dict(
                                color=TEXT, fontFamily="monospace", fontSize="11px",
                                background=BG, padding="8px", borderRadius="4px",
                                maxHeight="100px", overflow="auto", margin="0",
                                whiteSpace="pre-wrap", border=f"1px solid {BORDER}")),
                        ], style=dict(flex="1")),
                    ], style=dict(display="flex")),
                ]),
            ], style=dict(flex="1", padding="10px", minWidth="0")),

        ], style=dict(display="flex", flex="1", background=BG, minHeight="0")),
    ], style=dict(background=BG, minHeight="100vh", display="flex", flexDirection="column"))

    app.index_string = app.index_string.replace("</head>", """<style>
body{margin:0;background:#0d1117;}
.Select-control{background:#161b22!important;border-color:#30363d!important;color:#e6edf3!important;}
.Select-menu-outer{background:#161b22!important;border-color:#30363d!important;}
.Select-option{background:#161b22!important;color:#e6edf3!important;}
.Select-option:hover,.Select-option.is-focused{background:#21262d!important;}
.Select-value-label{color:#e6edf3!important;}
.Select-placeholder{color:#8b949e!important;}
.rc-slider-track{background-color:#388bfd;}
.rc-slider-handle{border-color:#388bfd;background:#388bfd;}
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:#0d1117;}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:3px;}
</style></head>""")

    # ══════════════════════════════════════════════════════════════════════
    #  CALLBACKS
    # ══════════════════════════════════════════════════════════════════════

    def _store_and_controls_from_parsed(parsed, filenames):
        store = dict(
            activities     = parsed["activities"].to_json(orient="split"),
            trades         = parsed["trades"].to_json(orient="split"),
            logs           = parsed["logs"].to_json(orient="split"),
            products       = parsed["products"],
            days           = [int(d) for d in parsed["days"]],
            day_boundaries = [int(b) for b in parsed["day_boundaries"]],
            mode           = parsed["mode"],
        )
        prod_opts = [{"label": p, "value": p} for p in parsed["products"]]
        sorted_days = sorted(parsed["days"])
        day_opts = ([{"label": "All days (stitched)", "value": "all"}] +
                    [{"label": f"Day {d}", "value": d} for d in sorted_days])
        act_cols   = parsed["activities"].select_dtypes("number").columns.tolist()
        price_cols = [c for c in act_cols if "price" in c or "mid" in c]
        norm_opts  = ([{"label": "None", "value": "none"}] +
                      [{"label": c, "value": c} for c in price_cols])
        days_str = ", ".join(f"Day {d}" for d in sorted_days)
        status = f"✓ {len(filenames)} file(s) · {len(parsed['products'])} products · {days_str}"
        return (store, prod_opts,
                parsed["products"][0] if parsed["products"] else None,
                day_opts, "all", norm_opts, status)

    @app.callback(
        Output("store-data",    "data"),
        Output("dd-product",    "options"),
        Output("dd-product",    "value"),
        Output("dd-day",        "options"),
        Output("dd-day",        "value"),
        Output("dd-norm",       "options"),
        Output("upload-status", "children"),
        Input("upload-files",   "contents"),
        State("upload-files",   "filename"),
        prevent_initial_call=True,
    )
    def load_files(contents_list, filenames):
        if not contents_list:
            return dash.no_update, [], None, [], "all", [{"label":"None","value":"none"}], ""
        files = [(name, base64.b64decode(c.split(",")[1]))
                 for c, name in zip(contents_list, filenames)]
        try:
            has_log = any(n.endswith(".log") for n, _ in files)
            parsed  = parse_log(files[0][1]) if has_log and len(files) == 1 \
                      else parse_csv_files(files)
        except Exception as e:
            return (dash.no_update, [], None, [], "all",
                    [{"label":"None","value":"none"}], f"❌ {e}")
        return _store_and_controls_from_parsed(parsed, filenames)

    @app.callback(
        Output("store-toggles", "data"),
        Output("btn-bids",      "style"),
        Output("btn-asks",      "style"),
        Output("btn-own",       "style"),
        Output("btn-market",    "style"),
        Input("btn-bids",       "n_clicks"),
        Input("btn-asks",       "n_clicks"),
        Input("btn-own",        "n_clicks"),
        Input("btn-market",     "n_clicks"),
        State("store-toggles",  "data"),
        prevent_initial_call=True,
    )
    def toggle_buttons(nb, na, no, nm, toggles):
        key_map = {"btn-bids":"bids","btn-asks":"asks","btn-own":"own","btn-market":"market"}
        if ctx.triggered_id in key_map:
            k = key_map[ctx.triggered_id]
            toggles[k] = not toggles[k]
        return (toggles, _btn_style(toggles["bids"]), _btn_style(toggles["asks"]),
                _btn_style(toggles["own"]), _btn_style(toggles["market"]))

    @app.callback(
        Output("main-chart",     "figure"),
        Output("pnl-chart",      "figure"),
        Output("pos-chart",      "figure"),
        Output("chart-subtitle", "children"),
        Output("stats-panel",    "children"),
        Input("store-data",      "data"),
        Input("dd-product",      "value"),
        Input("dd-day",          "value"),
        Input("dd-norm",         "value"),
        Input("store-toggles",   "data"),
        Input("qty-slider",      "value"),
        prevent_initial_call=True,
    )
    def update_charts(store, product, day_filter, norm_col, toggles, qty_range):
        if store is None or product is None:
            return _empty_fig(440), _empty_fig(150), _empty_fig(150), "", ""

        activities     = pd.read_json(io.StringIO(store["activities"]), orient="split")
        trades         = pd.read_json(io.StringIO(store["trades"]),     orient="split")
        day_boundaries = store.get("day_boundaries", [])
        days           = store.get("days", [])

        if not trades.empty and "trade_type" not in trades.columns:
            trades["trade_type"] = "market"

        day_f  = day_filter if day_filter is not None else "all"
        norm   = None if norm_col == "none" else norm_col
        min_q, max_q = (qty_range[0], qty_range[1]) if qty_range else (0, 9999)
        bounds = day_boundaries if day_f == "all" else []

        mf = build_main_figure(activities, trades, product, day_f,
                               toggles.get("bids",True), toggles.get("asks",True),
                               toggles.get("own",True), toggles.get("market",True),
                               norm, min_q, max_q, bounds, days)
        pf = build_pnl_figure(activities, product, day_f, bounds, days)
        psf= build_position_figure(trades, product, day_f, bounds)

        day_label = "All days" if day_f=="all" else f"Day {day_f}"
        subtitle  = f"{product} · {day_label}" + (f" · Δ{norm}" if norm else "")

        act_p = activities[activities["product"]==product]
        if day_f!="all" and "day" in act_p.columns:
            act_p = act_p[act_p["day"]==int(day_f)]
        tr_p = trades[trades["product"]==product] if not trades.empty else pd.DataFrame()
        if day_f!="all" and not tr_p.empty and "day" in tr_p.columns:
            tr_p = tr_p[tr_p["day"]==int(day_f)]

        final_pnl = (act_p["profit_and_loss"].iloc[-1]
                     if not act_p.empty and "profit_and_loss" in act_p.columns else 0)
        tt = tr_p.get("trade_type", pd.Series(dtype=str)) if not tr_p.empty else pd.Series(dtype=str)
        our = tr_p[tt.isin(["our_buy","our_sell"])] if not tr_p.empty and len(tt) else pd.DataFrame()
        mkt = tr_p[tt=="market"]                     if not tr_p.empty and len(tt) else pd.DataFrame()

        def sc(v): return MARKET_COL if v>0 else (ASK_COL if v<0 else TEXT_DIM)
        stats = html.Div([
            html.Div([html.Span("Final PnL  ", style=dict(color=TEXT_DIM)),
                      html.Span(f"{final_pnl:+.2f}", style=dict(color=sc(final_pnl)))]),
            html.Div([html.Span("Our trades ", style=dict(color=TEXT_DIM)),
                      html.Span(str(len(our)), style=dict(color=TEXT))]),
            html.Div([html.Span("Mkt trades ", style=dict(color=TEXT_DIM)),
                      html.Span(str(len(mkt)), style=dict(color=TEXT))]),
            html.Div([html.Span("Our vol    ", style=dict(color=TEXT_DIM)),
                      html.Span(str(int(our["quantity"].sum())) if not our.empty else "0",
                                style=dict(color=TEXT))]),
        ])
        return mf, pf, psf, subtitle, stats

    @app.callback(
        Output("log-sandbox",  "children"),
        Output("log-lambda",   "children"),
        Output("log-ts-label", "children"),
        Input("main-chart",    "hoverData"),
        State("store-data",    "data"),
        prevent_initial_call=True,
    )
    def update_logs(hover_data, store):
        if hover_data is None or store is None:
            return "— no log —", "— no log —", ""
        try:
            ts = hover_data["points"][0]["x"]
        except (KeyError, IndexError):
            return "— no log —", "— no log —", ""
        logs = pd.read_json(io.StringIO(store["logs"]), orient="split")
        if logs.empty:
            return "— CSV mode: no algo logs —", "— CSV mode: no algo logs —", f"ts ≈ {ts}"
        idx = (logs["timestamp"] - ts).abs().idxmin()
        row = logs.iloc[idx]
        sb  = row.get("sandboxLog","") or ""
        lb  = row.get("lambdaLog", "") or ""
        return (sb or "— empty —", lb or "— empty —", f"ts = {int(row['timestamp'])}")

    if initial_paths:
        @app.callback(
            Output("store-data",    "data",     allow_duplicate=True),
            Output("dd-product",    "options",  allow_duplicate=True),
            Output("dd-product",    "value",    allow_duplicate=True),
            Output("dd-day",        "options",  allow_duplicate=True),
            Output("dd-day",        "value",    allow_duplicate=True),
            Output("dd-norm",       "options",  allow_duplicate=True),
            Output("upload-status", "children", allow_duplicate=True),
            Input("store-data",     "data"),
            prevent_initial_call="initial_call",
        )
        def preload(_):
            files = [(Path(p).name, Path(p).read_bytes()) for p in initial_paths]
            try:
                has_log = any(n.endswith(".log") for n, _ in files)
                parsed  = parse_log(files[0][1]) if has_log and len(files) == 1 \
                          else parse_csv_files(files)
            except Exception as e:
                return (dash.no_update,[], None, [], "all",
                        [{"label":"None","value":"none"}], f"❌ {e}")
            return _store_and_controls_from_parsed(parsed, [Path(p).name for p in initial_paths])

    return app


if __name__ == "__main__":
    paths = sys.argv[1:] or None
    app = create_app(initial_paths=paths)
    print("\n  Prosperity 4 Dashboard")
    print("  ───────────────────────")
    if paths:
        print(f"  Loaded: {', '.join(paths)}")
    else:
        print("  Drop prices_*.csv + trades_*.csv (or a .log) in the browser.")
    print("  http://localhost:8050\n")
    app.run(debug=False, host="0.0.0.0", port=8050)