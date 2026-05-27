"""Generate per-round analysis charts from shipped CSVs.

Dark theme matching existing docs/plots/*.png. Outputs into docs/plots/round_N/.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path("/Users/jakubpiotrowski/dtu-quant-lab-imc-prosperity-4")
OUT = REPO / "docs" / "plots"

# Theme — match the existing 4 plots (#0B1B33 navy + gold highlight)
BG = "#0B1B33"
FG = "#E6ECF5"
GRID = "#1F3658"
GOLD = "#F4C430"
BLUE = "#4FB6FF"
GREEN = "#4ADE80"
RED = "#F87171"
PURPLE = "#A78BFA"
ORANGE = "#FB923C"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "axes.edgecolor": GRID,
    "axes.labelcolor": FG,
    "axes.titlecolor": FG,
    "xtick.color": FG,
    "ytick.color": FG,
    "grid.color": GRID,
    "text.color": FG,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 11,
    "figure.dpi": 130,
    "savefig.dpi": 130,
    "savefig.facecolor": BG,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.25,
})


def style_ax(ax, title=None):
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(axis="both", which="major", labelsize=10)


def load_prices(round_n: int, day: int) -> pd.DataFrame:
    p = REPO / f"round_{round_n}" / "algorithmic" / "data" / f"prices_round_{round_n}_day_{day}.csv"
    return pd.read_csv(p, sep=";")


# ─────────────────────────────────────────── ROUND 1 ───────────────────────────────────────────


def r1_osmium_stationarity():
    df = load_prices(1, 0)
    osm = df[df["product"] == "ASH_COATED_OSMIUM"].copy()
    mids = osm["mid_price"].values

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    # Left: histogram of mid around peg
    ax = axes[0]
    ax.hist(mids, bins=50, color=GOLD, alpha=0.85, edgecolor=BG, linewidth=0.5)
    ax.axvline(10000, color=BLUE, linestyle="--", linewidth=2, label="Fair value peg @ 10,000")
    ax.axvline(np.mean(mids), color=GREEN, linestyle=":", linewidth=2, label=f"Observed mean = {np.mean(mids):.1f}")
    ax.set_xlabel("Mid price")
    ax.set_ylabel("Frequency")
    ax.legend(loc="upper left", framealpha=0.85, facecolor=BG, edgecolor=GRID)
    style_ax(ax, "ASH_COATED_OSMIUM — mid-price distribution (day 0)")

    # Right: ACF showing fast mean reversion (manual ACF)
    ax = axes[1]
    x = mids - np.mean(mids)
    n = len(x)
    max_lag = 50
    acf = np.array([np.corrcoef(x[:-k], x[k:])[0, 1] if k > 0 else 1.0 for k in range(max_lag + 1)])
    ax.stem(range(max_lag + 1), acf, linefmt=GOLD, markerfmt="o", basefmt=GRID)
    # half-life from AR(1) coef
    ar1 = acf[1]
    half_life = -np.log(2) / np.log(abs(ar1)) if 0 < abs(ar1) < 1 else float("inf")
    ax.axhline(0, color=FG, linewidth=0.6)
    ax.axhline(0.5, color=GRID, linewidth=0.6, linestyle=":")
    ax.set_xlabel("Lag (ticks)")
    ax.set_ylabel("Autocorrelation")
    ax.text(0.95, 0.95, f"AR(1) ρ = {ar1:.3f}\nhalf-life ≈ {half_life:.1f} ticks",
            transform=ax.transAxes, ha="right", va="top", fontsize=11,
            bbox=dict(facecolor=BG, edgecolor=GOLD, alpha=0.9, pad=8))
    style_ax(ax, "OSMIUM autocorrelation — mean-reverting signature")

    plt.suptitle("Round 1 · OSMIUM is textbook pegged + mean-reverting", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(OUT / "round_1" / "osmium_stationarity.png")
    plt.close()
    print(f"  → osmium_stationarity.png (ρ={ar1:.3f}, hl={half_life:.1f})")


def r1_pepper_drift():
    df = load_prices(1, 0)
    pep = df[df["product"] == "INTARIAN_PEPPER_ROOT"].copy().reset_index(drop=True)
    t = pep["timestamp"].values
    mids = pep["mid_price"].values
    # OLS fit
    a, b = np.polyfit(t, mids, 1)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(t, mids, color=BLUE, linewidth=1.0, alpha=0.8, label="Mid price")
    ax.plot(t, a * t + b, color=GOLD, linewidth=2.5, label=f"OLS drift = +{a*100:.4f} / 100 ticks")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Mid price")
    ax.legend(loc="lower right", framealpha=0.85, facecolor=BG, edgecolor=GRID)
    style_ax(ax, "INTARIAN_PEPPER_ROOT — slow deterministic drift (day 0)")
    ax.text(0.02, 0.97, f"slope = {a:+.5f} / tick\nintercept = {b:.2f}",
            transform=ax.transAxes, ha="left", va="top", fontsize=10,
            bbox=dict(facecolor=BG, edgecolor=GOLD, alpha=0.85, pad=6))
    plt.tight_layout()
    plt.savefig(OUT / "round_1" / "pepper_drift.png")
    plt.close()
    print(f"  → pepper_drift.png (drift={a:+.5f}/tick)")


# ─────────────────────────────────────────── ROUND 2 ───────────────────────────────────────────


def r2_regime_compare():
    # R2 added no new products. Show cross-day stability that let us up size.
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for prod, ax, color in [
        ("ASH_COATED_OSMIUM", axes[0], GOLD),
        ("INTARIAN_PEPPER_ROOT", axes[1], BLUE),
    ]:
        for day, alpha in [(-1, 0.55), (0, 0.75), (1, 1.0)]:
            df = load_prices(2, day)
            sub = df[df["product"] == prod].sort_values("timestamp")
            ax.plot(sub["timestamp"], sub["mid_price"], color=color, alpha=alpha, linewidth=0.9, label=f"day {day}")
        ax.legend(loc="upper right", framealpha=0.85, facecolor=BG, edgecolor=GRID, ncol=3)
        ax.set_ylabel("Mid price")
        style_ax(ax, f"{prod} — cross-day mids (R2 backtest data)")
    axes[1].set_xlabel("Timestamp")
    plt.suptitle("Round 2 · Same products, three days — confirming regime stability before sizing up",
                 fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(OUT / "round_2" / "cross_day_stability.png")
    plt.close()
    print("  → cross_day_stability.png")


def r2_spread_distribution():
    df = load_prices(2, 0)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, prod, color in [
        (axes[0], "ASH_COATED_OSMIUM", GOLD),
        (axes[1], "INTARIAN_PEPPER_ROOT", BLUE),
    ]:
        sub = df[df["product"] == prod]
        spread = (sub["ask_price_1"] - sub["bid_price_1"]).dropna()
        ax.hist(spread, bins=range(int(spread.min()), int(spread.max()) + 2),
                color=color, edgecolor=BG, linewidth=0.5, alpha=0.85)
        ax.axvline(spread.mean(), color=GREEN, linestyle="--", linewidth=1.5,
                   label=f"mean = {spread.mean():.2f}")
        ax.legend(loc="upper right", framealpha=0.85, facecolor=BG, edgecolor=GRID)
        ax.set_xlabel("Best-bid / best-ask spread (ticks)")
        ax.set_ylabel("Frequency")
        style_ax(ax, prod)
    plt.suptitle("Round 2 · Touch-spread distributions — sets the market-maker quote width",
                 fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(OUT / "round_2" / "spread_distribution.png")
    plt.close()
    print("  → spread_distribution.png")


# ─────────────────────────────────────────── ROUND 3 ───────────────────────────────────────────


def r3_hydrogel_drift_problem():
    """The catastrophic drift on HP that broke our R3 trader."""
    fig, ax = plt.subplots(figsize=(12, 5))
    for day, color, label in [
        (0, GOLD, "day 0"),
        (1, ORANGE, "day 1"),
        (2, RED, "day 2"),
    ]:
        df = load_prices(3, day)
        sub = df[df["product"] == "HYDROGEL_PACK"].sort_values("timestamp").reset_index(drop=True)
        # Re-anchor each day to its own start for visual comparison of drift magnitude
        baseline = sub["mid_price"].iloc[0]
        ax.plot(sub["timestamp"], sub["mid_price"] - baseline, color=color,
                linewidth=1.1, alpha=0.85, label=f"{label} (start = {baseline:.0f})")
    ax.axhline(0, color=FG, linewidth=0.6, alpha=0.5)
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Mid drift from session start (ticks)")
    ax.legend(loc="lower left", framealpha=0.85, facecolor=BG, edgecolor=GRID)
    style_ax(ax, "HYDROGEL_PACK — within-session drift broke our pegged-MM (R3)")
    ax.text(0.98, 0.97,
            "The static market-maker that worked on\nOSMIUM kept buying into this drawdown.\nThe regime-detector fix (PINNED / TRENDING /\nNOISY) only made it into the R4 trader.",
            transform=ax.transAxes, ha="right", va="top", fontsize=10,
            bbox=dict(facecolor=BG, edgecolor=RED, alpha=0.9, pad=10))
    plt.tight_layout()
    plt.savefig(OUT / "round_3" / "hydrogel_drift.png")
    plt.close()
    print("  → hydrogel_drift.png")


def r3_vev_vol_smile():
    """Implied vol per strike at the most active timestamp."""
    df = load_prices(3, 1)
    # Pull underlying mid per timestamp
    und = df[df["product"] == "VELVETFRUIT_EXTRACT"].set_index("timestamp")["mid_price"]
    strikes = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]

    # Pick a timestamp where every strike has a mid
    options = {K: df[df["product"] == f"VEV_{K}"].set_index("timestamp")["mid_price"] for K in strikes}
    common = und.index
    for s in options.values():
        common = common.intersection(s.index)
    ts = common[len(common) // 2]  # mid-session

    S = und.loc[ts]

    # Black-Scholes inversion via bisection (no scipy.stats needed)
    def norm_cdf(x):
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def bs_call(S, K, T, sigma, r=0.0):
        if sigma <= 0 or T <= 0:
            return max(S - K, 0.0)
        d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

    def implied_vol(price, S, K, T):
        if price <= max(S - K, 0) + 1e-6:
            return float("nan")
        lo, hi = 1e-4, 5.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if bs_call(S, K, T, mid) > price:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    # R3 vouchers: roughly 4 ticks/day, mid-of-session ~ 6 of 10 days left
    T = 6 / 365.0
    ivs = []
    moneys = []
    for K in strikes:
        price = options[K].loc[ts]
        iv = implied_vol(price, S, K, T)
        if not math.isnan(iv) and iv < 3:
            ivs.append(iv)
            moneys.append(math.log(K / S))

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.scatter(moneys, ivs, s=80, color=GOLD, edgecolor=FG, linewidth=1, zorder=3, label="Observed IV per strike")
    if len(ivs) >= 3:
        coefs = np.polyfit(moneys, ivs, 2)
        xx = np.linspace(min(moneys), max(moneys), 100)
        ax.plot(xx, np.polyval(coefs, xx), color=BLUE, linewidth=2,
                label=f"Parabolic fit  σ(m) = {coefs[0]:.2f}m² + {coefs[1]:.2f}m + {coefs[2]:.2f}")
    ax.axvline(0, color=GRID, linewidth=0.8, linestyle=":")
    ax.set_xlabel("log-moneyness  m = log(K / S)")
    ax.set_ylabel("Implied volatility")
    ax.legend(loc="upper right", framealpha=0.85, facecolor=BG, edgecolor=GRID)
    style_ax(ax, f"VEV voucher chain — implied-vol smile (R3 day 1, t = {ts})")
    ax.text(0.02, 0.97, f"S = {S:.1f}\n{len(ivs)} of 10 strikes invertible\nT ≈ {T*365:.0f} days",
            transform=ax.transAxes, ha="left", va="top", fontsize=10,
            bbox=dict(facecolor=BG, edgecolor=GOLD, alpha=0.9, pad=8))
    plt.tight_layout()
    plt.savefig(OUT / "round_3" / "vev_vol_smile.png")
    plt.close()
    print(f"  → vev_vol_smile.png (S={S:.1f}, {len(ivs)} strikes)")


# ─────────────────────────────────────────── ROUND 4 ───────────────────────────────────────────


def r4_regime_detector():
    """Hydrogel mid + a rolling z-score showing how the 3-state regime detector classifies."""
    df = load_prices(4, 2)
    hp = df[df["product"] == "HYDROGEL_PACK"].sort_values("timestamp").reset_index(drop=True)
    mids = hp["mid_price"].values
    ts = hp["timestamp"].values
    # Rolling median anchor + rolling std
    window = 500
    pad = mids.copy().astype(float)
    med = pd.Series(pad).rolling(window, min_periods=50).median().values
    std = pd.Series(pad).rolling(window, min_periods=50).std().values
    z = (mids - med) / np.where(std > 0, std, 1)

    # Classify
    PINNED = np.abs(z) < 0.5
    TRENDING = np.abs(z) >= 1.5
    NOISY = ~PINNED & ~TRENDING

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1]})
    ax = axes[0]
    ax.plot(ts, mids, color=BLUE, linewidth=0.9, alpha=0.8, label="HYDROGEL mid")
    ax.plot(ts, med, color=GOLD, linewidth=1.6, label=f"Rolling-{window} median anchor")
    ax.fill_between(ts, med - 1.5 * std, med + 1.5 * std, color=GOLD, alpha=0.12, label="±1.5σ band")
    ax.set_ylabel("Mid price")
    ax.legend(loc="lower left", framealpha=0.85, facecolor=BG, edgecolor=GRID)
    style_ax(ax, "HYDROGEL_PACK — R4 regime-detector overlay (day 2)")

    ax = axes[1]
    ax.fill_between(ts, -0.5, 0.5, color=GREEN, alpha=0.18, label="PINNED zone (|z|<0.5)")
    ax.axhline(1.5, color=ORANGE, linewidth=1, linestyle="--", alpha=0.7)
    ax.axhline(-1.5, color=ORANGE, linewidth=1, linestyle="--", alpha=0.7, label="TRENDING threshold (|z|≥1.5)")
    ax.plot(ts, z, color=FG, linewidth=0.7, alpha=0.85)
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("z-score vs rolling median")
    ax.legend(loc="upper right", framealpha=0.85, facecolor=BG, edgecolor=GRID, fontsize=9)
    style_ax(ax)

    n_p = int(np.nansum(PINNED))
    n_t = int(np.nansum(TRENDING))
    n_n = int(np.nansum(NOISY))
    n_all = n_p + n_t + n_n
    axes[0].text(0.02, 0.97,
                 f"PINNED  {100*n_p/n_all:.1f}%\nTRENDING  {100*n_t/n_all:.1f}%\nNOISY  {100*n_n/n_all:.1f}%",
                 transform=axes[0].transAxes, ha="left", va="top", fontsize=10,
                 bbox=dict(facecolor=BG, edgecolor=GOLD, alpha=0.9, pad=8))
    plt.tight_layout()
    plt.savefig(OUT / "round_4" / "hydrogel_regime.png")
    plt.close()
    print(f"  → hydrogel_regime.png ({100*n_p/n_all:.0f}/{100*n_t/n_all:.0f}/{100*n_n/n_all:.0f} %)")


def r4_voucher_chain():
    """Voucher market price vs Black-Scholes fair at one snapshot."""
    df = load_prices(4, 2)
    und = df[df["product"] == "VELVETFRUIT_EXTRACT"].set_index("timestamp")["mid_price"]
    strikes = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]
    options = {K: df[df["product"] == f"VEV_{K}"].set_index("timestamp")["mid_price"] for K in strikes}

    common = und.index
    for s in options.values():
        common = common.intersection(s.index)
    ts = common[len(common) // 2]
    S = und.loc[ts]

    def norm_cdf(x):
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def bs_call(S, K, T, sigma, r=0.0):
        if sigma <= 0 or T <= 0:
            return max(S - K, 0.0)
        d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

    T = 5 / 365.0
    sigma = 0.20  # our R3 flat anchor for comparison
    market = [options[K].loc[ts] for K in strikes]
    fair = [bs_call(S, K, T, sigma) for K in strikes]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(strikes))
    width = 0.38
    ax.bar(x - width / 2, market, width=width, color=GOLD, edgecolor=BG, linewidth=0.5, label="Market price")
    ax.bar(x + width / 2, fair, width=width, color=BLUE, edgecolor=BG, linewidth=0.5,
           label=f"BS fair (σ = {sigma:.2f} flat)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"VEV_{K}" for K in strikes], rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("Voucher price")
    ax.legend(loc="upper right", framealpha=0.85, facecolor=BG, edgecolor=GRID)
    style_ax(ax, f"VEV voucher chain — market vs Black-Scholes fair (R4 day 2, t = {ts}, S = {S:.0f})")
    ax.text(0.02, 0.97,
            "A flat-σ anchor over- and under-prices\nsymmetrically — the R3 trader missed\nmost of this edge. R4 added a parabolic\nIV correction and recovered some of it.",
            transform=ax.transAxes, ha="left", va="top", fontsize=10,
            bbox=dict(facecolor=BG, edgecolor=GOLD, alpha=0.9, pad=8))
    plt.tight_layout()
    plt.savefig(OUT / "round_4" / "voucher_market_vs_fair.png")
    plt.close()
    print(f"  → voucher_market_vs_fair.png (S={S:.0f})")


# ─────────────────────────────────────────── ROUND 5 ───────────────────────────────────────────


def r5_pebbles_basket_constraint():
    """The keystone alpha: PEBBLES_XS + S + M + L + XL ≈ 50,000."""
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5))

    # Left: time series of basket sum across all 3 days
    ax = axes[0]
    all_sums = []
    for day, color in [(2, GOLD), (3, ORANGE), (4, RED)]:
        df = load_prices(5, day)
        pebs = ["PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"]
        per = {p: df[df["product"] == p].set_index("timestamp")["mid_price"] for p in pebs}
        common = per[pebs[0]].index
        for s in per.values():
            common = common.intersection(s.index)
        basket = sum(per[p].loc[common] for p in pebs)
        ax.plot(common, basket.values, color=color, linewidth=0.8, alpha=0.85,
                label=f"day {day}  μ={basket.mean():.1f}  σ={basket.std():.2f}")
        all_sums.append(basket.values)
    ax.axhline(50000, color=BLUE, linestyle="--", linewidth=1.5, label="50,000 constraint")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Σ PEBBLES (XS+S+M+L+XL)")
    ax.legend(loc="upper right", framealpha=0.9, facecolor=BG, edgecolor=GRID, fontsize=9)
    style_ax(ax, "PEBBLES basket sum — near-deterministic across all 3 days")

    # Right: histogram of all observations
    ax = axes[1]
    pooled = np.concatenate(all_sums)
    ax.hist(pooled - 50000, bins=60, color=GOLD, alpha=0.85, edgecolor=BG, linewidth=0.5)
    ax.axvline(0, color=BLUE, linestyle="--", linewidth=1.5)
    ax.set_xlabel("Deviation from 50,000")
    ax.set_ylabel("Frequency")
    ax.text(0.95, 0.95,
            f"All days, all ticks pooled (n = {len(pooled):,})\nrange  [{pooled.min():.0f}, {pooled.max():.0f}]\nstd  σ = {pooled.std():.2f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=10,
            bbox=dict(facecolor=BG, edgecolor=GOLD, alpha=0.9, pad=8))
    style_ax(ax, "Deviation histogram — σ ≈ 3 across thousands of ticks")
    plt.suptitle("Round 5 keystone · PEBBLES basket-sum constraint (cleanest alpha of the round)",
                 fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(OUT / "round_5" / "pebbles_basket_constraint.png")
    plt.close()
    print(f"  → pebbles_basket_constraint.png (σ={pooled.std():.2f}, n={len(pooled):,})")


def r5_oxygen_shake_dislocation():
    """OXYGEN_SHAKE_CHOCOLATE — the +587k product."""
    fig, ax = plt.subplots(figsize=(12, 5))
    for day, color in [(2, GOLD), (3, ORANGE), (4, RED)]:
        df = load_prices(5, day)
        osc = df[df["product"] == "OXYGEN_SHAKE_CHOCOLATE"].sort_values("timestamp")
        ax.plot(osc["timestamp"], osc["mid_price"], color=color, linewidth=0.9, alpha=0.85,
                label=f"day {day}  μ={osc['mid_price'].mean():.1f}  σ={osc['mid_price'].std():.1f}")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Mid price")
    ax.legend(loc="upper right", framealpha=0.85, facecolor=BG, edgecolor=GRID)
    style_ax(ax, "OXYGEN_SHAKE_CHOCOLATE — the +587,831 carry product (R5)")
    ax.text(0.02, 0.97,
            "Wide, persistent book.\nA plain inside-spread market-making post\ncompounded into 97% of the round 5 PnL.\nThis was the breakthrough.",
            transform=ax.transAxes, ha="left", va="top", fontsize=10,
            bbox=dict(facecolor=BG, edgecolor=GOLD, alpha=0.9, pad=8))
    plt.tight_layout()
    plt.savefig(OUT / "round_5" / "oxygen_shake_chocolate.png")
    plt.close()
    print("  → oxygen_shake_chocolate.png")


def r5_product_universe():
    """All 50 products, mid-price range bar chart — shows the structural variety."""
    df = load_prices(5, 2)
    summary = df.groupby("product")["mid_price"].agg(["min", "max", "mean"]).sort_values("mean")
    fig, ax = plt.subplots(figsize=(11, 12))
    y = np.arange(len(summary))
    ax.hlines(y, summary["min"], summary["max"], color=GOLD, alpha=0.6, linewidth=1.5)
    ax.scatter(summary["mean"], y, color=BLUE, s=20, zorder=3, label="Mean mid")
    ax.set_yticks(y)
    ax.set_yticklabels(summary.index, fontsize=8)
    ax.set_xlabel("Mid price")
    ax.legend(loc="lower right", framealpha=0.85, facecolor=BG, edgecolor=GRID)
    # Colour-band by cluster
    cluster_keys = ["PEBBLES", "SNACKPACK", "MICROCHIP", "OXYGEN_SHAKE", "PANEL",
                    "UV_VISOR", "TRANSLATOR", "GALAXY_SOUNDS", "ROBOT", "SLEEP_POD"]
    cluster_colors = {k: c for k, c in zip(cluster_keys,
        [GOLD, BLUE, GREEN, RED, PURPLE, ORANGE, "#22D3EE", "#F472B6", "#FACC15", "#94A3B8"])}
    for yi, name in enumerate(summary.index):
        cluster = next((k for k in cluster_keys if name.startswith(k)), None)
        if cluster:
            ax.hlines(yi, summary.iloc[yi]["min"], summary.iloc[yi]["max"],
                      color=cluster_colors[cluster], alpha=0.7, linewidth=2)
    style_ax(ax, "Round 5 product universe — 50 names in 10 clusters (day 2 mid range)")
    plt.tight_layout()
    plt.savefig(OUT / "round_5" / "product_universe.png")
    plt.close()
    print(f"  → product_universe.png ({len(summary)} products)")


def r5_cluster_correlations():
    """Cluster-level correlation heatmap from day 2 returns."""
    df = load_prices(5, 2)
    wide = df.pivot_table(index="timestamp", columns="product", values="mid_price", aggfunc="last")
    wide = wide.ffill().dropna(how="any")
    # Per-cluster mean returns
    clusters = {
        "PEBBLES": [p for p in wide.columns if p.startswith("PEBBLES")],
        "SNACKPACK": [p for p in wide.columns if p.startswith("SNACKPACK")],
        "MICROCHIP": [p for p in wide.columns if p.startswith("MICROCHIP")],
        "OXYGEN_SHAKE": [p for p in wide.columns if p.startswith("OXYGEN_SHAKE")],
        "PANEL": [p for p in wide.columns if p.startswith("PANEL")],
        "UV_VISOR": [p for p in wide.columns if p.startswith("UV_VISOR")],
        "TRANSLATOR": [p for p in wide.columns if p.startswith("TRANSLATOR")],
        "GALAXY_SOUNDS": [p for p in wide.columns if p.startswith("GALAXY_SOUNDS")],
        "ROBOT": [p for p in wide.columns if p.startswith("ROBOT")],
        "SLEEP_POD": [p for p in wide.columns if p.startswith("SLEEP_POD")],
    }
    rets = wide.pct_change().dropna()
    cluster_rets = pd.DataFrame({name: rets[cols].mean(axis=1) for name, cols in clusters.items()})
    corr = cluster_rets.corr()

    fig, ax = plt.subplots(figsize=(9, 7.5))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=10)
    ax.set_yticklabels(corr.columns, fontsize=10)
    for i in range(len(corr.columns)):
        for j in range(len(corr.columns)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}",
                    ha="center", va="center", fontsize=8,
                    color="white" if abs(corr.values[i, j]) > 0.5 else FG)
    cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.ax.tick_params(labelsize=9)
    style_ax(ax, "Round 5 · Cluster-mean return correlations (day 2)")
    plt.tight_layout()
    plt.savefig(OUT / "round_5" / "cluster_correlations.png")
    plt.close()
    print("  → cluster_correlations.png")


# ─────────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Round 1 ...")
    r1_osmium_stationarity()
    r1_pepper_drift()
    print("Round 2 ...")
    r2_regime_compare()
    r2_spread_distribution()
    print("Round 3 ...")
    r3_hydrogel_drift_problem()
    r3_vev_vol_smile()
    print("Round 4 ...")
    r4_regime_detector()
    r4_voucher_chain()
    print("Round 5 ...")
    r5_pebbles_basket_constraint()
    r5_oxygen_shake_dislocation()
    r5_product_universe()
    r5_cluster_correlations()
    print("Done.")
