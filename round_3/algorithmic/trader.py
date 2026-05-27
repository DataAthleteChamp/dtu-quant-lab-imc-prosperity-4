"""
DTU Quant Lab — IMC Prosperity 4 — Round 3 Trader (v09a: v08 + 4 quick-win patches)
====================================================================
v09a additions over v08:
  Patch 1: VEV deep-OTM absolute edge — when voucher_mid < 10, override edge=1
            (replaces old K=5500-specific 0.3·spread override; tighter and more general).
  Patch 2: K=5100 tighter edge sweep — edge = max(1, V09A_EDGE_MULT_5100 · spread).
            Sweep winner will be baked in. Default=0.35.
  Patch 3: VEV_5300 outlier → suppress passive smile MM — when the per-day outlier
            flag (vev5300_day_outlier) is latched, ALSO zero out passive MM orders for
            K=5300 (not just MR overlay). Anchor still contributes to smile fit.
  Patch 4: HP EOD window sweep — eod_window swept over {8500,9000,9200,9500,10000}.
            Winner baked in. Default kept at v08 winner=8500 until sweep confirms.

DTU Quant Lab — IMC Prosperity 4 — Round 3 Trader (v08: v07 + HP EOD flatten + VEV_5300 outlier detector)
====================================================================
v07 additions over v06h:
  - HP regime detector is now 3-state: PINNED / TRENDING / NOISY.
  - TRENDING regime fires when |EMA_short(50) - EMA_long(500)| > k * sigma,
    regardless of sigma level. Uses a rolling-median anchor (window=200)
    instead of a fixed FV, with max_pos=50, edge=6, and bid/ask size skew
    that leans inventory WITH the drift (so net inventory follows mid as it
    drifts, instead of the v06h bug where static FV=9990 + max_pos=200 kept
    buying all the way down through a 70-tick HP drawdown on live d2).
  - PINNED + NOISY behavior unchanged from v06h.
v07_orig_header_below
====================================================================

Products handled in this single file:
  Legacy Phase-1 (still tradable, still PnL):
    - ASH_COATED_OSMIUM         (R2 OSMIUM logic, verbatim)
    - INTARIAN_PEPPER_ROOT      (R2 PEPPER logic, verbatim)
  New in Round 3:
    - HYDROGEL_PACK             (independent stationary spot, OSMIUM-style MM)
    - VELVETFRUIT_EXTRACT (VEV) (mean-reverting underlying + delta-hedge leg)
    - VEV_K  for K ∈ {4000,4500,5000,5100,5200,5300,5400,5500,6000,6500}
                                (European call vouchers; BS-MM around single σ)

Voucher strategy (jmerle 9th-place P2 R4 template, scaled to 6 strikes):
    S = mid(VELVETFRUIT_EXTRACT)   (anchored EMA of mid)
    T = (TTE_DAYS_LIVE − ts/1e6) / 365     # 1 round = 1 Solvenarian day
    σ = SIGMA_GLOBAL  (default 0.25; flat IV surface verified empirically)
    fair = BS_CALL(S, K, T, 0, σ)
    edge = max(2, 0.4 · avg_spread(K))
    if mid_K > fair + edge:  swing position toward −limit
    elif mid_K < fair − edge: swing position toward +limit
    Skip 4000/4500/6000/6500 (no time edge or dead at 0.5).

Delta-hedge overlay:
    D = Σ_K δ_K · pos_K
    Reduce exposure via VEV_EXTRACT spot orders when |D| > HEDGE_TRIGGER.

Phase 2 context:
    Only R3 + R4 + R5 count for the championship; vouchers persist across
    rounds with TTE = 5 → 4 → 3 days. Same trader.py is reused per round
    with TTE_DAYS_LIVE decremented in PARAMS_VOUCHER.

Self-contained — stdlib only — never crashes (every product wrapped in try).
"""

import json
import math
from statistics import NormalDist
from typing import Any, Dict, List, Optional, Tuple

from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState

# ── v09a sweep knobs (overridden by sweep harness via module attribute patching) ──
# Patch 2: K=5100 edge multiplier — edge = max(pv["min_edge"], V09A_EDGE_MULT_5100 · spread).
# FIX (V2): floor changed from 1.0 → pv["min_edge"] (=0.1). Old floor=1.0 was WIDER than
# vega edge ~0.775 so it hurt 5100. With floor=0.1, em=0.25 gives edge=0.25*spread which is
# tighter than vega on most ticks. Cap +2,600 vs disable; live +30.
V09A_EDGE_MULT_5100: float = 0.25
# Patch 4: HP EOD window — sweep winner = 9200 (HP live +106 vs baseline +8500).
V09A_EOD_WINDOW: int = 9200

# ── Logger (compressed, jmerle visualizer compatible) ──────────────────────

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict, conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""]))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders), conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [state.timestamp, td,
                [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
                {s: [od.buy_orders, od.sell_orders] for s, od in state.order_depths.items()},
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp] for arr in state.own_trades.values() for t in arr],
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp] for arr in state.market_trades.values() for t in arr],
                state.position,
                [state.observations.plainValueObservations,
                 {p: [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff, o.importTariff, o.sugarPrice, o.sunlightIndex]
                  for p, o in state.observations.conversionObservations.items()}]]

    def compress_orders(self, orders):
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, value):
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        lo, hi = 0, min(len(value), max_length)
        out = ""
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = value[:mid]
            if len(candidate) < len(value):
                candidate += "..."
            if len(json.dumps(candidate)) <= max_length:
                out = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return out


logger = Logger()


# ── Configuration ──────────────────────────────────────────────────────────

# Position limits (community-confirmed for Phase 2). Override via BT --limit too.
LIMITS: Dict[str, int] = {
    "ASH_COATED_OSMIUM": 80,
    "INTARIAN_PEPPER_ROOT": 80,
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    "VEV_4000": 300, "VEV_4500": 300, "VEV_5000": 300, "VEV_5100": 300,
    "VEV_5200": 300, "VEV_5300": 300, "VEV_5400": 300, "VEV_5500": 300,
    "VEV_6000": 300, "VEV_6500": 300,
}

# OSMIUM / PEPPER (R2 verbatim)
PARAMS_OSMIUM = {
    "fair_value": 10000, "imb_mult": 0.0, "inv_skew": 0.0,
    "flatten_t1": 48, "flatten_t2": 60,
}
PARAMS_PEPPER = {"slope": 0.001}

# HYDROGEL_PACK — live R3 (sub 386720, 387009) shows mean ≈ 9979, std ≈ 30,
# range 9915-10031. MM around any anchor bleeds in this regime (sub 387009
# lost −7,780 with wide-clamp MM; sub 386720 lost −377 with narrow clamp
# that mostly didn't trade). Switch to TAKE-ONLY mode by default.
PARAMS_HYDROGEL = {
    # v04d: Avellaneda-Stoikov limit-order MM. HP mid≈9979, σ_returns≈2.27,
    # ACF(1)=−0.143 (mean-reverting). Reservation price skews against inventory
    # so we don't get adversely selected by directional flow. Skip MM when
    # |mid - EMA| > dev_skip_k · σ (informed flow regime).
    # Tuned via grid sweep on capsule day0/1/2 + live day3 (round3/_sweep_v04d_fine.log):
    # winner = g=0.05, k=0.3, sz=3, dev=2.5 → cap [+1589, +2799, +193], live +60.
    "disabled": False,
    "ema_alpha": 0.05,              # slow EMA for mean reference
    "sigma_window": 100,            # rolling window for σ of mid-price diffs
    "sigma_init": 2.27,             # warm-up σ before window fills
    "gamma": 0.05,                  # risk aversion
    "k": 0.3,                       # arrival intensity
    "T_t": 1.0,                     # session fraction remaining
    "max_size": 3,                  # max units per quote side
    "dev_skip_k": 2.5,              # skip MM if |mid - EMA| > k·σ
    "min_half_spread": 1,           # at least 1 tick away from mid
}

# v06h: regime-aware dispatch. Detect σ of mid-returns over a rolling window;
# in PINNED regime use Frankfurt StaticTrader (v06a), in NOISY regime fall back
# to v05 A-S MM. Hysteresis dead-zone between the two thresholds.
PARAMS_HP_REGIME = {
    # v06h sweep winner (sweep_v06h_results.json): regime detector cleanly
    # separates pinned-vs-noisy days. Capsule days 0/1/2: ~99% pinned →
    # Frankfurt StaticTrader earns +17,593 HP (vs v05 +4,581 baseline).
    # Live day 3: 100% noisy → falls back to v05 A-S MM, HP=+60 (exact match).
    "regime_window": 200,
    "vol_thresh_low": 2.0,
    "vol_thresh_high": 5.0,
    "warmup_ticks": 100,
    "default_regime": "pinned",     # capsule heavily pinned; mid σ ~2.15 sits in dead-zone so default sticks
    "static_fv_anchor": 9990.0,
    "static_take_edge": 3.0,
    "static_penny_jump": True,
    "static_flatten_at_fv": False,
    "static_make_size_pos": 200,
    "static_max_pos": 200,
    "log_regime": False,
    # v07 drift detector — sweep winner (sweep_v07_hp_drift_results.json,
    # 39/108 passing; maximin pick: k=2.0, ema_s=50, ema_l=500, tmp=30,
    # trend_handler="freeze"). Live d2: HP +417→+7613, trough −8583→+1545,
    # total +6154→+13350. Capsule HP all positive: (+26464, +9317, +12470).
    "drift_ema_short": 50,
    "drift_ema_long": 500,
    "drift_thresh_k": 2.0,
    "trend_max_pos": 30,
    "trend_edge_mult": 2.0,
    "trend_anchor_window": 200,
    "trend_lean_size": 30,
    "drift_min_displacement": 0.0,    # 0 = displacement gate disabled
    # TRENDING handler mode:
    #   "freeze"  — emit no orders (let inherited position ride; sweep winner).
    #   "static_skewed" — rolling-median anchor + size lean (described in task).
    "trend_handler": "freeze",
    # v08 — take-profit / flatten / cool-down re-entry. The v07 freeze handler
    # rode short pos=−160 from peak HP +14,737 down to +7,569 on live d2
    # (submission 432994). Three layers added to lock in profits. After the
    # parameter sweep (sweep_v08_hp_takeprofit_results.json) the WINNING
    # configuration is **EOD-only flatten**: trailing stop and cool-down both
    # fire too aggressively in capsule (where TRENDING blips occur in
    # mean-reverting PINNED days) and locked-in losses outweighed live gains.
    # The EOD flatten with mtm-floor (eod_min_pnl=12000) and eod_window=8500
    # lets live d2 fire at ts=91,500 (near global peak HP +14,993) yielding
    # HP +7,613 → +12,037, while capturing a +7,202 trending blip on cap_d2
    # and leaving cap_d0 / cap_d1 untouched (gate never fires there).
    #
    # Layer 1: Trailing stop on HP MTM PnL — DISABLED by sweep winner.
    "tp_enabled": False,
    "tp_min_pos": 50,
    "tp_drawdown_thresh": 1500.0,
    "tp_min_hwm": 12000.0,
    # Layer 2: Cool-down re-entry to PINNED — DISABLED. The TRENDING regime
    # on live d2 didn't compress enough to trigger cool-down before EOD.
    "cool_enabled": False,
    "k_cool": 0.5,
    "N_cool": 200,
    # Layer 3: Hard EOD flatten (last 10k ticks) — primary mechanism.
    # Gated on (regime=="trending") AND |pos|>=eod_min_pos AND mtm>=eod_min_pnl
    # to avoid crystallizing PINNED inventory or small loss-making positions.
    "eod_enabled": True,
    "eod_window": V09A_EOD_WINDOW,  # v09a Patch 4: sweep {8500,9000,9200,9500,10000}
    "eod_min_pnl": 12000.0,
    "eod_min_pos": 50,
}

# VELVETFRUIT_EXTRACT spot — empirical day-0..day-2: mean ≈ 5250, std ≈ 14,
# range ≈ 5200..5285. Fair = wide-clamp EMA of mid; take only on >3-tick miss.
PARAMS_VEV_SPOT = {
    "anchor_init": 5250.0, "anchor_alpha": 0.10,
    "anchor_clamp": (5210.0, 5290.0),
    "take_thresh": 3.0,
    "soft_cap_frac": 0.30,          # MM keeps |pos| ≤ 60 of 200 (light MM)
    "post_dist": 2,
    "make_disabled": True,
    # v04e: short-EMA mean-reversion overlay on EXTRACT mid.
    # VELVETFRUIT (underlying) ACF(1)=-0.172. Front-runs FV-anchored TAKE
    # using a faster EMA(10) and a tick-deviation threshold; capped per tick.
    "mr_enabled": True,
    "mr_ema_window": 20,
    "mr_k_thr": 5.0,
    "mr_max_size": 20,
}

# Vouchers — single global σ; per-strike overrides allowed.
# Empirical IV at TTE=7d ≈ 0.256 (verified from capsule day-0/1/2 mids).
PARAMS_VOUCHER = {
    "tte_days_live": 5,             # R3 live = 5d. R4 → 4. R5 → 3. Capsule BT
                                    # auto-handles via day_count rollover (set
                                    # to 7 only if BT-ing capsule day 0 alone).
    "sigma_global": 0.256,
    "auto_iv": True,                # solve σ from ATM voucher each tick;
                                    # protects against wrong TTE assumption.
    "auto_iv_strike": 5300,         # liquid ATM strike (mid spot ≈ 5260)
    "auto_iv_alpha": 0.05,          # EMA on solved σ
    "auto_iv_min": 0.10, "auto_iv_max": 0.40,
    "edge_floor": 2.0,
    "edge_frac": 0.8,
    "active_strikes": (5000, 5100, 5200, 5300),
    "skip_strikes": (4000, 4500, 5400, 5500, 6000, 6500),
    "limit_frac": 0.7,              # MM headroom; take fills the rest
    "swing_size_frac": 1.0,         # bang-to-limit on signal (jmerle template)
    "min_strike_spread_for_make": 2,
}

# v05a — smile-aware parabolic IV passive MM.
# Fits IV(m) = a·m² + b·m + c via OLS over LIQUID strikes each tick where
# m = log(K/S) / sqrt(T). Coeffs EMA-smoothed. Fair = BS(S, K, T, smile_IV).
# Quotes posted PASSIVE only (never cross). TAKE only when deeply mispriced.
PARAMS_VOUCHER_V05 = {
    "tte_days_live": 5,
    "liquid_strikes": (5000, 5100, 5200, 5300, 5400, 5500),  # KEEP 5400 for fit anchor
    "enable_strikes": (4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500),
    "dead_strikes": (6000, 6500),
    "parabola_ema_alpha": 0.01,
    "min_edge": 0.1,
    "edge_take_mult": 1.5,
    "iv_uncertainty": 0.005,
    "max_pos_per_strike": 200,
    "quote_size": 20,
    "dead_edge_mult": 5.0,
    "min_strikes_for_fit": 4,
    "iv_min": 0.10,
    "iv_max": 0.40,
    # v06g knobs:
    #   skip_quote_strikes: K stays in liquid_strikes (fit anchor) but no
    #     quotes are posted and no take orders are issued for it.
    #   wide_edge_strikes: per-K multiplicative edge bump (applied AFTER
    #     dead_edge_mult); defends against single-strike anomalies (e.g. K=5400)
    #     without removing the strike from quoting.
    "skip_quote_strikes": (5400, 5200),
    "wide_edge_strikes": {},
}

# v05c: per-strike voucher EMA-mean-reversion overlay (additive on top of v05a quotes).
# Live day-3 ACF(1) on voucher mids: VEV_5300=-0.15, VEV_5400=-0.19, VEV_5500=-0.21.
# Tuned via greedy per-strike sweep (round3/experiments/sweep_v05c_results.json).
PARAMS_VOUCHER_MR = {
    5300: {"enabled": True, "W": 40, "k_thr": 3.0, "max_size": 30},
    5400: {"enabled": False, "W": 20, "k_thr": 1.0, "max_size": 10},
    5500: {"enabled": True, "W": 40, "k_thr": 1.0, "max_size": 30},
}

# v07 VEV_5300 regime gate — only the K=5300 MR overlay is gated. K=5500 keeps
# its current (working) v05c behavior. BT/live calibration shows BT runs the
# 5300 MR overlay 1.78× hotter than live (live 1,221 vs BT-window 2,170,
# capsule full-day −653 over 3 days = −2,305). The hypothesis is that the
# overlay fires on noise that doesn't materialize live; a regime filter should
# trim those false fires while keeping the real edge.
#
# Gate semantics (all that are enabled below must pass for the overlay to fire):
#   1. realized_match : |sigma_real(window) - sigma_implied| < sigma_match_thresh
#                       sigma_implied is the smile level coefficient (c, ATM IV),
#                       converted to per-tick stdev of voucher mid via vega.
#   2. vmid_sigma_max : rolling stdev of voucher VEV_5300 mid is below band
#                       (low-vol regime).
#   3. min_warmup_ticks: skip first N ticks of the day.
#   4. max_spread_ticks: only fire when (ask - bid) <= N ticks.
PARAMS_VEV_5300_GATE = {
    "enabled": True,
    "use_realized_match": False,
    "sigma_realized_window": 60,
    "sigma_match_thresh": 0.05,
    "use_vmid_sigma": False,
    "vmid_sigma_window": 100,
    "vmid_sigma_max": 1.5,
    "use_warmup": True,
    "min_warmup_ticks": 100,
    "use_spread": True,
    "max_spread_ticks": 2,
}


# v08 Branch B: per-day outlier detector. After `detect_ticks` ticks of warmup,
# evaluate rolling realized vol of vmid returns (or vmid stdev). If above
# threshold, flag whole day as outlier — disables K=5300 MR overlay rest of
# day. Sweep winner: detect_ticks=300, use_realized=True, realized_max=0.55
# yields capsule d1 +458 (-2417 → -1959) with live d3 V53 unchanged at +2166.
PARAMS_VEV_5300_OUTLIER = {
    "enabled": True,
    "detect_ticks": 300,
    "vmid_sigma_window": 200,
    "vmid_sigma_max": 1.5,
    "use_realized": True,
    "realized_window": 200,
    "realized_max": 0.55,
}


# Delta hedge overlay — empirically (capsule sweep) hedging costs > vega
# protection: trigger=999 effectively disables hedge. Re-evaluate on live data.
PARAMS_HEDGE = {
    "trigger": 999,                 # disabled by default
    "priority_trigger": 9999,
}


# ── Order-book helpers ─────────────────────────────────────────────────────

def get_best_bid_ask(order_depth: OrderDepth) -> Tuple[Optional[int], Optional[int]]:
    bb = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
    ba = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
    return bb, ba


def get_mid_price(order_depth: OrderDepth) -> Optional[float]:
    bb, ba = get_best_bid_ask(order_depth)
    if bb is None or ba is None:
        return None
    return (bb + ba) / 2.0


def get_micro_price(order_depth: OrderDepth) -> Optional[float]:
    bb, ba = get_best_bid_ask(order_depth)
    if bb is None or ba is None:
        return None
    bvol = abs(order_depth.buy_orders[bb])
    avol = abs(order_depth.sell_orders[ba])
    tot = bvol + avol
    if tot == 0:
        return (bb + ba) / 2.0
    return (bb * avol + ba * bvol) / tot


# ── Black-Scholes (stdlib only) ────────────────────────────────────────────

_NORMAL = NormalDist()
_SQRT2 = math.sqrt(2.0)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def bs_call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes European call price. Robust to T<=0 and σ<=0 (returns intrinsic)."""
    if T <= 0.0 or sigma <= 0.0 or S <= 0.0:
        return max(0.0, S - K)
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)


def bs_call_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0.0 or sigma <= 0.0 or S <= 0.0:
        return 1.0 if S > K else 0.0
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    return _norm_cdf(d1)


def bs_call_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0.0 or sigma <= 0.0 or S <= 0.0:
        return 0.0
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    return S * _norm_pdf(d1) * sqrtT


def implied_vol(price: float, S: float, K: float, T: float, r: float = 0.0,
                sigma_init: float = 0.25, max_iter: int = 30, tol: float = 1e-5) -> Optional[float]:
    """Newton's method on σ for BS_CALL. Returns None if not convergent."""
    intrinsic = max(0.0, S - K * math.exp(-r * T))
    if price < intrinsic - 1e-6 or price > S:
        return None
    sigma = max(1e-3, sigma_init)
    for _ in range(max_iter):
        p = bs_call_price(S, K, T, r, sigma)
        v = bs_call_vega(S, K, T, r, sigma)
        if v < 1e-8:
            return None
        diff = p - price
        if abs(diff) < tol:
            return sigma
        sigma -= diff / v
        if sigma <= 1e-4:
            sigma = 1e-4
        if sigma > 5.0:
            sigma = 5.0
    return sigma


# ── OSMIUM (R2 verbatim) ──────────────────────────────────────────────────

def trade_osmium(state: TradingState, saved: dict) -> List[Order]:
    product = "ASH_COATED_OSMIUM"
    if product not in state.order_depths:
        return []
    params = PARAMS_OSMIUM
    order_depth = state.order_depths[product]
    position = state.position.get(product, 0)
    limit = LIMITS[product]

    bb, ba = get_best_bid_ask(order_depth)
    if bb is not None and ba is not None:
        mid_ema = (bb + ba) / 2.0
        if "osm_fv" not in saved:
            saved["osm_fv"] = 10000.0
        saved["osm_fv"] = 0.98 * saved["osm_fv"] + 0.02 * mid_ema
        fair_anchor = max(9997.0, min(10003.0, saved["osm_fv"]))
    else:
        fair_anchor = params["fair_value"]
    fair_value = float(fair_anchor)

    orders: List[Order] = []
    buy_used = 0
    sell_used = 0
    max_buy = max(0, limit - position)
    max_sell = max(0, limit + position)

    ADVERSE_VOL = 20 if state.timestamp < 10000 else 30
    for ask_price in sorted(order_depth.sell_orders.keys()):
        if ask_price < fair_value and buy_used < max_buy:
            ask_vol = abs(order_depth.sell_orders[ask_price])
            if ask_vol < ADVERSE_VOL and (fair_value - ask_price) < 2:
                continue
            qty = min(ask_vol, max_buy - buy_used)
            if qty > 0:
                orders.append(Order(product, ask_price, qty)); buy_used += qty
    for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
        if bid_price > fair_value and sell_used < max_sell:
            bid_vol = abs(order_depth.buy_orders[bid_price])
            if bid_vol < ADVERSE_VOL and (bid_price - fair_value) < 2:
                continue
            qty = min(bid_vol, max_sell - sell_used)
            if qty > 0:
                orders.append(Order(product, bid_price, -qty)); sell_used += qty

    est_position = position + buy_used - sell_used
    remaining_buy = max(0, limit - est_position)
    remaining_sell = max(0, limit + est_position)

    bb0, ba0 = get_best_bid_ask(order_depth)
    if bb0 is not None and ba0 is not None:
        spread_obs = ba0 - bb0
        mid_obs = (bb0 + ba0) / 2.0
        safe_mode = spread_obs > 35 or abs(mid_obs - fair_value) > 30
    elif bb0 is None and ba0 is None:
        safe_mode = True
    else:
        safe_mode = False

    if est_position >= params["flatten_t2"] and not safe_mode:
        flat_sell_thresh = fair_value - 4
    elif est_position >= params["flatten_t1"] and not safe_mode:
        flat_sell_thresh = fair_value - 1
    else:
        flat_sell_thresh = fair_value
    if est_position <= -params["flatten_t2"] and not safe_mode:
        flat_buy_thresh = fair_value + 4
    elif est_position <= -params["flatten_t1"] and not safe_mode:
        flat_buy_thresh = fair_value + 1
    else:
        flat_buy_thresh = fair_value

    if est_position > 0:
        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price >= flat_sell_thresh and remaining_sell > 0:
                bid_vol = abs(order_depth.buy_orders[bid_price])
                qty = min(bid_vol, remaining_sell, est_position)
                if qty > 0:
                    orders.append(Order(product, bid_price, -qty))
                    remaining_sell -= qty; est_position -= qty
            else:
                break
    elif est_position < 0:
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price <= flat_buy_thresh and remaining_buy > 0:
                ask_vol = abs(order_depth.sell_orders[ask_price])
                qty = min(ask_vol, remaining_buy, abs(est_position))
                if qty > 0:
                    orders.append(Order(product, ask_price, qty))
                    remaining_buy -= qty; est_position += qty
            else:
                break

    remaining_buy = max(0, limit - est_position)
    remaining_sell = max(0, limit + est_position)

    best_bid, best_ask = get_best_bid_ask(order_depth)
    bv = abs(order_depth.buy_orders.get(best_bid, 0)) if best_bid is not None else 0
    av = abs(order_depth.sell_orders.get(best_ask, 0)) if best_ask is not None else 0
    tot_q = bv + av
    qi_best = (bv - av) / (tot_q + 1e-9) if tot_q > 0 else 0.0
    qr_shallow = 0 < tot_q < 25
    qr_bull = qr_shallow and qi_best >= 0.3
    qr_bear = qr_shallow and qi_best <= -0.3
    buy_scale = 0.2 if (qr_bear and not safe_mode) else 1.0
    sell_scale = 0.2 if (qr_bull and not safe_mode) else 1.0

    fv_int = int(round(fair_anchor))
    bp = fv_int - 2
    ap = fv_int + 2
    if best_bid is not None and best_bid < fair_value:
        bp = min(best_bid + 1, fv_int - 1)
    if best_ask is not None and best_ask > fair_value:
        ap = max(best_ask - 1, fv_int + 1)

    if remaining_buy > 0:
        rb = int(remaining_buy * buy_scale)
        b1 = int(rb * 0.6); b2 = rb - b1
        if b1 > 0: orders.append(Order(product, bp, b1))
        if b2 > 0 and bp - 1 < fv_int: orders.append(Order(product, bp - 1, b2))
    if remaining_sell > 0:
        rs = int(remaining_sell * sell_scale)
        s1 = int(rs * 0.6); s2 = rs - s1
        if s1 > 0: orders.append(Order(product, ap, -s1))
        if s2 > 0 and ap + 1 > fv_int: orders.append(Order(product, ap + 1, -s2))
    return orders


# ── PEPPER (R2 verbatim, simplified) ───────────────────────────────────────

def trade_pepper(state: TradingState, saved: dict) -> List[Order]:
    product = "INTARIAN_PEPPER_ROOT"
    if product not in state.order_depths:
        return []
    order_depth = state.order_depths[product]
    position = state.position.get(product, 0)
    limit = LIMITS[product]
    slope = PARAMS_PEPPER["slope"]

    mid = get_mid_price(order_depth)
    if "pepper_start_price" not in saved and mid is not None:
        saved["pepper_start_price"] = mid
    if "pepper_first_mid" not in saved and mid is not None:
        saved["pepper_first_mid"] = mid

    if mid is not None and state.timestamp > 2000 and "pepper_first_mid" in saved:
        est_slope = (mid - saved["pepper_first_mid"]) / state.timestamp
        if 0 <= est_slope <= 0.005:
            slope = est_slope

    start_price = saved.get("pepper_start_price", mid or 10000)
    if mid is not None and abs(mid - (start_price + slope * state.timestamp)) > 500:
        saved["pepper_start_price"] = mid - slope * state.timestamp
        saved["pepper_first_mid"] = mid
        start_price = saved["pepper_start_price"]

    fair_trend = start_price + slope * state.timestamp
    if mid is not None and state.timestamp > 10000 and mid < start_price - 500:
        if position > 0:
            bb, _ = get_best_bid_ask(order_depth)
            if bb is not None:
                return [Order(product, bb, -position)]
        return []

    micro = get_micro_price(order_depth)
    fair_value = fair_trend + (micro - mid) if (micro is not None and mid is not None) else fair_trend

    orders: List[Order] = []
    buy_used = 0
    max_buy = max(0, limit - position)
    for ask_price in sorted(order_depth.sell_orders.keys()):
        if ask_price < fair_value and buy_used < max_buy:
            ask_vol = abs(order_depth.sell_orders[ask_price])
            qty = min(ask_vol, max_buy - buy_used)
            if qty > 0:
                orders.append(Order(product, ask_price, qty)); buy_used += qty

    est_position = position + buy_used
    remaining_buy = max(0, limit - est_position)
    if est_position < limit:
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price <= fair_value + 10 and remaining_buy > 0:
                ask_vol = abs(order_depth.sell_orders[ask_price])
                qty = min(ask_vol, remaining_buy)
                if qty > 0:
                    orders.append(Order(product, ask_price, qty))
                    remaining_buy -= qty; est_position += qty

    if remaining_buy > 0:
        bb, _ = get_best_bid_ask(order_depth)
        bp = int(round(fair_value))
        if bb is not None and bb + 1 < fair_value:
            bp = max(bp, bb + 1)
        orders.append(Order(product, bp, remaining_buy))

    if est_position >= limit - 5:
        scalp_qty = min(10, est_position)
        scalp_price = int(round(fair_value)) + 10
        orders.append(Order(product, scalp_price, -scalp_qty))
    return orders


# ── HYDROGEL_PACK (OSMIUM-style MM around adaptive anchor ≈ 9990) ─────────

def _trade_hp_as_mm(state: TradingState, saved: dict) -> List[Order]:
    """Avellaneda-Stoikov limit-order MM for HYDROGEL_PACK.

    Reservation price r = s - q·γ·σ²·(T-t) skews quotes against current
    inventory. Optimal half-spread δ = γ·σ²·(T-t) + (2/γ)·ln(1 + γ/k).
    Posts symmetric quotes around r at ±δ/2. Skips MM if mid is more than
    `dev_skip_k`·σ from the slow EMA (likely informed flow).
    """
    product = "HYDROGEL_PACK"
    p = PARAMS_HYDROGEL
    if p.get("disabled", False):
        return []
    if product not in state.order_depths:
        return []
    order_depth = state.order_depths[product]
    position = state.position.get(product, 0)
    limit = LIMITS[product]

    bb, ba = get_best_bid_ask(order_depth)
    if bb is None or ba is None:
        return []
    mid = (bb + ba) / 2.0

    # Rolling history for σ (std-dev of consecutive mid diffs).
    hist = saved.setdefault("hp_mids", [])
    hist.append(mid)
    win = p["sigma_window"]
    if len(hist) > win + 1:
        del hist[: len(hist) - (win + 1)]
    if len(hist) >= 5:
        diffs = [hist[i] - hist[i - 1] for i in range(1, len(hist))]
        n = len(diffs)
        mean = sum(diffs) / n
        var = sum((d - mean) ** 2 for d in diffs) / n
        sigma = var ** 0.5 if var > 0 else p["sigma_init"]
    else:
        sigma = p["sigma_init"]

    # Slow EMA reference for the dev-skip filter.
    ema = saved.get("hp_ema")
    if ema is None:
        ema = mid
    ema = (1 - p["ema_alpha"]) * ema + p["ema_alpha"] * mid
    saved["hp_ema"] = ema

    # Skip MM under suspected informed flow.
    if abs(mid - ema) > p["dev_skip_k"] * max(sigma, 1e-6):
        return []

    gamma = p["gamma"]
    k = p["k"]
    T_t = p["T_t"]
    sig2 = sigma * sigma

    r = mid - position * gamma * sig2 * T_t
    half_spread = 0.5 * (gamma * sig2 * T_t + (2.0 / gamma) * math.log(1.0 + gamma / k))
    half_spread = max(half_spread, p["min_half_spread"])

    bid_px = int(math.floor(r - half_spread))
    ask_px = int(math.ceil(r + half_spread))
    # Don't cross the book; quote at touch at worst.
    if bid_px >= ba:
        bid_px = ba - 1
    if ask_px <= bb:
        ask_px = bb + 1
    if ask_px <= bid_px:
        ask_px = bid_px + 1

    max_size = p["max_size"]
    remaining_buy = max(0, limit - position)
    remaining_sell = max(0, limit + position)
    bid_size = min(max_size, remaining_buy)
    ask_size = min(max_size, remaining_sell)

    orders: List[Order] = []
    if bid_size > 0:
        orders.append(Order(product, bid_px, bid_size))
    if ask_size > 0:
        orders.append(Order(product, ask_px, -ask_size))
    return orders


def _trade_hp_static(state: TradingState, saved: dict) -> List[Order]:
    """Frankfurt StaticTrader (TAKE / FLATTEN@FV / PENNY-JUMP) — pinned regime.

    Uses regime sub-params from PARAMS_HP_REGIME (static_*).
    """
    product = "HYDROGEL_PACK"
    rp = PARAMS_HP_REGIME
    if product not in state.order_depths:
        return []
    try:
        order_depth = state.order_depths[product]
        position = state.position.get(product, 0)
        limit = min(LIMITS[product], int(rp["static_max_pos"]))

        buys = order_depth.buy_orders
        sells = order_depth.sell_orders
        if not buys and not sells:
            return []

        fv = float(rp["static_fv_anchor"])
        take_edge = float(rp["static_take_edge"])

        orders: List[Order] = []
        buy_used = 0
        sell_used = 0
        max_buy = max(0, limit - position)
        max_sell = max(0, limit + position)

        # 1) TAKE
        for ask_px in sorted(sells.keys()):
            if ask_px >= fv - take_edge:
                break
            if buy_used >= max_buy:
                break
            qty = min(abs(sells[ask_px]), max_buy - buy_used)
            if qty > 0:
                orders.append(Order(product, int(ask_px), qty))
                buy_used += qty
        for bid_px in sorted(buys.keys(), reverse=True):
            if bid_px <= fv + take_edge:
                break
            if sell_used >= max_sell:
                break
            qty = min(abs(buys[bid_px]), max_sell - sell_used)
            if qty > 0:
                orders.append(Order(product, int(bid_px), -qty))
                sell_used += qty

        est_pos = position + buy_used - sell_used
        rem_buy = max(0, limit - est_pos)
        rem_sell = max(0, limit + est_pos)

        fv_int_below = int(math.floor(fv))
        fv_int_above = int(math.ceil(fv))

        # 2) FLATTEN at FV (optional)
        if rp["static_flatten_at_fv"]:
            if est_pos > 0 and rem_sell > 0:
                qty = min(est_pos, rem_sell)
                orders.append(Order(product, fv_int_above, -qty))
                rem_sell -= qty
            elif est_pos < 0 and rem_buy > 0:
                qty = min(-est_pos, rem_buy)
                orders.append(Order(product, fv_int_below, qty))
                rem_buy -= qty

        # 3) PENNY-JUMP
        if rp["static_penny_jump"]:
            bids_below = [px for px in buys.keys() if px < fv]
            asks_above = [px for px in sells.keys() if px > fv]
            make_size = int(rp["static_make_size_pos"])
            if bids_below and rem_buy > 0:
                make_bid = max(bids_below) + 1
                if make_bid <= fv_int_below - 1:
                    qty = min(make_size, rem_buy)
                    if qty > 0:
                        orders.append(Order(product, int(make_bid), qty))
                        rem_buy -= qty
            if asks_above and rem_sell > 0:
                make_ask = min(asks_above) - 1
                if make_ask >= fv_int_above + 1:
                    qty = min(make_size, rem_sell)
                    if qty > 0:
                        orders.append(Order(product, int(make_ask), -qty))
                        rem_sell -= qty

        return orders
    except Exception:
        return []


def _trade_hp_static_trend(state: TradingState, saved: dict) -> List[Order]:
    """v07 TRENDING handler — rolling-median anchor + tightened risk cap.

    Mirrors the PINNED static handler (TAKE / PENNY-JUMP), but swaps the fixed
    FV anchor (9990) for a rolling-median anchor over `trend_anchor_window`
    mids and tightens position cap to `trend_max_pos`. This way:
      * As mid drifts down (v06h's bug case), the anchor follows so we stop
        buying the falling knife.
      * Risk on a wrong-direction position is capped at trend_max_pos, not 200.
      * On capsule (false-positive trending in mean-reverting noise), behavior
        degrades gracefully: we still penny-jump symmetrically around the local
        median anchor, just with a smaller book — no directional bet that
        would bleed if the "trend" reverts.
    The wider edge (trend_edge_mult * static_take_edge) gives a buffer against
    chasing a still-drifting price right past the rolling anchor.
    A small WITH-drift size lean nudges inventory toward the trend direction,
    so a real persistent drift bleeds inventory without market-dumping.
    """
    product = "HYDROGEL_PACK"
    rp = PARAMS_HP_REGIME
    if product not in state.order_depths:
        return []
    try:
        order_depth = state.order_depths[product]
        position = state.position.get(product, 0)
        limit = min(LIMITS[product], int(rp["trend_max_pos"]))

        buys = order_depth.buy_orders
        sells = order_depth.sell_orders
        if not buys and not sells:
            return []

        mids_anchor = saved.get("hp_anchor_mids", [])
        if not mids_anchor:
            return []
        s = sorted(mids_anchor)
        n = len(s)
        anchor = s[n // 2] if n % 2 == 1 else 0.5 * (s[n // 2 - 1] + s[n // 2])

        take_edge = float(rp["static_take_edge"]) * float(rp["trend_edge_mult"])
        ema_s = saved.get("hp_drift_ema_short")
        ema_l = saved.get("hp_drift_ema_long")
        drift_sign = 0
        if ema_s is not None and ema_l is not None:
            if ema_s < ema_l:
                drift_sign = -1
            elif ema_s > ema_l:
                drift_sign = 1

        orders: List[Order] = []
        buy_used = 0
        sell_used = 0
        max_buy = max(0, limit - position)
        max_sell = max(0, limit + position)

        # 1) TAKE — symmetric, around rolling-median anchor with wide edge.
        for ask_px in sorted(sells.keys()):
            if ask_px >= anchor - take_edge:
                break
            if buy_used >= max_buy:
                break
            qty = min(abs(sells[ask_px]), max_buy - buy_used)
            if qty > 0:
                orders.append(Order(product, int(ask_px), qty))
                buy_used += qty
        for bid_px in sorted(buys.keys(), reverse=True):
            if bid_px <= anchor + take_edge:
                break
            if sell_used >= max_sell:
                break
            qty = min(abs(buys[bid_px]), max_sell - sell_used)
            if qty > 0:
                orders.append(Order(product, int(bid_px), -qty))
                sell_used += qty

        est_pos = position + buy_used - sell_used
        rem_buy = max(0, limit - est_pos)
        rem_sell = max(0, limit + est_pos)

        anchor_below = int(math.floor(anchor))
        anchor_above = int(math.ceil(anchor))

        # 2) PENNY-JUMP — symmetric around anchor, with a small WITH-drift
        # size lean (trend_lean_size). Caps stay below the make_size_pos used
        # in PINNED so a false-trending capsule run can't blow up.
        if rp["static_penny_jump"]:
            bids_below = [px for px in buys.keys() if px < anchor]
            asks_above = [px for px in sells.keys() if px > anchor]
            base_size = int(rp["trend_max_pos"])
            lean = int(rp["trend_lean_size"])
            if drift_sign < 0:
                bid_make_cap = max(0, base_size - lean)
                ask_make_cap = base_size
            elif drift_sign > 0:
                bid_make_cap = base_size
                ask_make_cap = max(0, base_size - lean)
            else:
                bid_make_cap = ask_make_cap = base_size

            if bids_below and rem_buy > 0 and bid_make_cap > 0:
                make_bid = max(bids_below) + 1
                if make_bid <= anchor_below - 1:
                    qty = min(bid_make_cap, rem_buy)
                    if qty > 0:
                        orders.append(Order(product, int(make_bid), qty))
                        rem_buy -= qty
            if asks_above and rem_sell > 0 and ask_make_cap > 0:
                make_ask = min(asks_above) - 1
                if make_ask >= anchor_above + 1:
                    qty = min(ask_make_cap, rem_sell)
                    if qty > 0:
                        orders.append(Order(product, int(make_ask), -qty))
                        rem_sell -= qty

        return orders
    except Exception:
        return []


def trade_hydrogel(state: TradingState, saved: dict) -> List[Order]:
    """v06h regime-aware HP dispatcher.

    Maintains rolling mid-price history; computes σ of consecutive returns;
    classifies regime as PINNED (low vol → Frankfurt StaticTrader) or NOISY
    (high vol → v05 Avellaneda-Stoikov MM). Hysteresis dead-zone between
    vol_thresh_low and vol_thresh_high preserves the previous regime.

    Position cap (LIMITS) is honoured by both sub-strategies regardless of
    regime, so flips don't violate risk limits even with a partial position
    inherited from the prior regime.
    """
    product = "HYDROGEL_PACK"
    rp = PARAMS_HP_REGIME
    if product not in state.order_depths:
        return []

    order_depth = state.order_depths[product]
    bb, ba = get_best_bid_ask(order_depth)

    # Maintain rolling regime history of mids.
    rhist = saved.setdefault("hp_regime_mids", [])
    if bb is not None and ba is not None:
        mid_now = (bb + ba) / 2.0
        rhist.append(mid_now)
        win = int(rp["regime_window"])
        if len(rhist) > win:
            del rhist[: len(rhist) - win]

        # v07: maintain anchor window (rolling-median anchor for TRENDING).
        ahist = saved.setdefault("hp_anchor_mids", [])
        ahist.append(mid_now)
        aw = int(rp["trend_anchor_window"])
        if len(ahist) > aw:
            del ahist[: len(ahist) - aw]

        # v07: dual EMAs for drift detection.
        es = saved.get("hp_drift_ema_short")
        el = saved.get("hp_drift_ema_long")
        a_s = 2.0 / (float(rp["drift_ema_short"]) + 1.0)
        a_l = 2.0 / (float(rp["drift_ema_long"]) + 1.0)
        es = mid_now if es is None else (1 - a_s) * es + a_s * mid_now
        el = mid_now if el is None else (1 - a_l) * el + a_l * mid_now
        saved["hp_drift_ema_short"] = es
        saved["hp_drift_ema_long"] = el

    # Compute σ of mid-PRICE LEVELS over the regime_window (per spec:
    # "rolling_sigma(window=200)"). Earlier v06h used σ of returns; for the
    # drift detector we want a normalization that sees "is the drift large
    # vs typical price dispersion", which is level-σ. Both are kept under
    # different names so existing PINNED hysteresis still works.
    sigma_lvl = None
    sigma_ret = None
    if len(rhist) >= 5:
        # level σ
        m = sum(rhist) / len(rhist)
        v = sum((x - m) ** 2 for x in rhist) / len(rhist)
        sigma_lvl = v ** 0.5
        # return σ (existing definition for PINNED/NOISY classification)
        diffs = [rhist[i] - rhist[i - 1] for i in range(1, len(rhist))]
        n = len(diffs)
        mu = sum(diffs) / n
        v = sum((d - mu) ** 2 for d in diffs) / n
        sigma_ret = v ** 0.5
    sigma = sigma_ret  # vol_thresh_low/high keep return-σ semantics

    # Decide regime with hysteresis. Default applies during warmup.
    cur = saved.get("hp_regime", rp["default_regime"])
    es = saved.get("hp_drift_ema_short")
    el = saved.get("hp_drift_ema_long")
    if len(rhist) < int(rp["warmup_ticks"]) or sigma is None or es is None or el is None or sigma_lvl is None:
        regime = rp["default_regime"]
    else:
        lo = float(rp["vol_thresh_low"])
        hi = float(rp["vol_thresh_high"])
        k_thr = float(rp["drift_thresh_k"])
        diff = abs(es - el)
        # Use LEVEL-σ over `regime_window` for drift normalization (matches
        # the detector spec: "EMA(short) − EMA(long) > k · rolling_sigma(200)").
        sig_eff = max(sigma_lvl, 1e-6)
        is_trending = diff > k_thr * sig_eff
        # Optional price-action confirmation: require the rolling-median anchor
        # to have actually displaced from the static FV before firing TRENDING.
        # Set drift_min_displacement=0 to disable the gate (default; sweep
        # winner uses freeze-on-detection so the gate isn't needed).
        min_disp = float(rp.get("drift_min_displacement", 0.0))
        if is_trending and min_disp > 0.0:
            ahist = saved.get("hp_anchor_mids", [])
            if ahist:
                ss = sorted(ahist)
                nn = len(ss)
                med = ss[nn // 2] if nn % 2 == 1 else 0.5 * (ss[nn // 2 - 1] + ss[nn // 2])
                if abs(med - float(rp["static_fv_anchor"])) < min_disp:
                    is_trending = False
        if is_trending:
            regime = "trending"
        elif cur == "trending":
            # HYSTERESIS: only leave TRENDING when drift is well below threshold
            # AND sigma is in the low band; otherwise stay in TRENDING. This
            # prevents the v06h bug where a brief drift-pause during a deep
            # downtrend let PINNED re-engage with anchor=9990 + max_pos=200.
            if diff < 0.5 * k_thr * sig_eff and sigma < lo:
                regime = "pinned"
            elif diff < 0.5 * k_thr * sig_eff and sigma > hi:
                regime = "noisy"
            else:
                regime = "trending"
        elif sigma < lo:
            regime = "pinned"
        elif sigma > hi:
            regime = "noisy"
        else:
            regime = cur
    saved["hp_regime"] = regime

    # ─── v08: cost-basis tracking (running avg from HP own_trades) and
    # mark-to-market PnL (cash + pos*mid). HWM is on MTM PnL because the
    # BT-displayed HP PnL is the same quantity, and we want trailing stop
    # to lock in HP-PnL at peak (which includes prior realized round-trips).
    pos_now = state.position.get(product, 0)
    cb_pos = saved.get("hp_cb_pos", 0)
    cb_avg = saved.get("hp_cb_avg", 0.0)
    cash = saved.get("hp_cash", 0.0)
    last_trade_ts = saved.get("hp_last_trade_ts", -1)
    new_last_trade_ts = last_trade_ts
    for t in state.own_trades.get(product, []) or []:
        if t.timestamp <= last_trade_ts:
            continue
        q = int(t.quantity)
        if q <= 0:
            continue
        signed_q = q if t.buyer == "SUBMISSION" else -q
        cash -= float(t.price) * signed_q
        new_pos = cb_pos + signed_q
        if cb_pos == 0:
            cb_avg = float(t.price)
        elif (cb_pos > 0 and signed_q > 0) or (cb_pos < 0 and signed_q < 0):
            cb_avg = (cb_avg * abs(cb_pos) + float(t.price) * abs(signed_q)) / abs(new_pos)
        else:
            if abs(signed_q) < abs(cb_pos):
                pass
            elif abs(signed_q) == abs(cb_pos):
                cb_avg = 0.0
            else:
                cb_avg = float(t.price)
        cb_pos = new_pos
        if t.timestamp > new_last_trade_ts:
            new_last_trade_ts = t.timestamp
    if cb_pos == 0:
        cb_avg = 0.0
    saved["hp_cb_pos"] = cb_pos
    saved["hp_cb_avg"] = cb_avg
    saved["hp_cash"] = cash
    saved["hp_last_trade_ts"] = new_last_trade_ts

    if pos_now != cb_pos and bb is not None and ba is not None:
        # Defensive re-anchor (warmup race conditions).
        if pos_now == 0:
            cb_avg = 0.0
        else:
            cb_avg = (bb + ba) / 2.0
        cb_pos = pos_now
        saved["hp_cb_pos"] = cb_pos
        saved["hp_cb_avg"] = cb_avg

    mid_now = None
    if bb is not None and ba is not None:
        mid_now = (bb + ba) / 2.0
    mtm_pnl = cash + pos_now * mid_now if mid_now is not None else cash

    # ─── v08 Layer 2: cool-down re-entry counter (TRENDING → PINNED) ──────
    if rp.get("cool_enabled", False) and regime == "trending" and \
       sigma_lvl is not None and es is not None and el is not None:
        k_cool = float(rp.get("k_cool", 0.5))
        n_cool = int(rp.get("N_cool", 200))
        diff_now = abs(es - el)
        sig_eff_cool = max(sigma_lvl, 1e-6)
        if diff_now < k_cool * sig_eff_cool:
            saved["hp_cool_count"] = saved.get("hp_cool_count", 0) + 1
        else:
            saved["hp_cool_count"] = 0
        if saved.get("hp_cool_count", 0) >= n_cool:
            regime = "pinned"
            saved["hp_regime"] = regime
            saved["hp_cool_count"] = 0
            # also reset HWM since we're exiting the trend
            saved.pop("hp_tp_hwm", None)
    else:
        saved["hp_cool_count"] = 0

    # ─── v08 Layer 1: trailing stop on HP MTM PnL (matches BT-displayed) ──
    # Only arm if (a) regime == "trending", (b) |pos| >= tp_min_pos, and
    # (c) HWM has reached at least tp_min_hwm (avoids firing on a small
    # early local peak during a much larger drift).
    flatten_now = False
    flatten_reason = None
    tp_min_pos = int(rp.get("tp_min_pos", 50))
    if rp.get("tp_enabled", False) and regime == "trending" and abs(pos_now) >= tp_min_pos:
        hwm = saved.get("hp_tp_hwm")
        if hwm is None or mtm_pnl > hwm:
            hwm = mtm_pnl
            saved["hp_tp_hwm"] = hwm
        dd = float(rp.get("tp_drawdown_thresh", 1500.0))
        tp_min_hwm = float(rp.get("tp_min_hwm", 0.0))
        if hwm >= tp_min_hwm and hwm - mtm_pnl >= dd:
            flatten_now = True
            flatten_reason = "trailing_stop"
    else:
        if abs(pos_now) < tp_min_pos or regime != "trending":
            saved.pop("hp_tp_hwm", None)

    # ─── v08 Layer 3: hard EOD flatten (TRENDING + profit gate) ───────────
    # Only fire if (a) regime == "trending" (don't crystallize PINNED
    # mean-reverting inventory) and (b) current MTM PnL is >= eod_min_pnl
    # (don't lock in losses; let mean-revert if behind).
    if rp.get("eod_enabled", False) and pos_now != 0 and regime == "trending":
        eod_w = int(rp.get("eod_window", 0))
        eod_min_pnl = float(rp.get("eod_min_pnl", 0.0))
        eod_min_pos = int(rp.get("eod_min_pos", 0))
        # EOD detection: live submission has ts max 99_900 (1k ticks), capsule
        # has ts max 999_900 (10k ticks). Fire only in the LAST eod_w ts of the
        # full episode in either case. Track running max ts to detect mode.
        ts_now = int(state.timestamp)
        ep_max_seen = int(saved.get("hp_eod_ts_max_seen", 0))
        if ts_now > ep_max_seen:
            saved["hp_eod_ts_max_seen"] = ts_now
            ep_max_seen = ts_now
        # Capsule day length is 1_000_000; live is 100_000. Use 1_000_000 if
        # we've ever seen ts > 100_000, else 100_000.
        ep_len = 1_000_000 if ep_max_seen >= 100_000 else 100_000
        eod_trigger = ts_now >= (ep_len - eod_w)
        if eod_w > 0 and eod_trigger \
                and mtm_pnl >= eod_min_pnl and abs(pos_now) >= eod_min_pos:
            flatten_now = True
            flatten_reason = flatten_reason or "eod"

    # Track regime distribution per-day for diagnostics.
    counts = saved.setdefault("hp_regime_counts", {"pinned": 0, "trending": 0, "noisy": 0})
    counts[regime] = counts.get(regime, 0) + 1
    try:
        _t = globals().get("Trader")
        if _t is not None:
            _t.HP_REGIME_COUNTS[regime] = _t.HP_REGIME_COUNTS.get(regime, 0) + 1
    except Exception:
        pass

    # Emit flatten orders crossing the touch, capped by visible book depth.
    if flatten_now and pos_now != 0:
        orders: List[Order] = []
        remaining = abs(pos_now)
        if pos_now > 0:
            # Sell into bids.
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if remaining <= 0:
                    break
                bvol = abs(order_depth.buy_orders[bid_price])
                qty = min(bvol, remaining)
                if qty > 0:
                    orders.append(Order(product, int(bid_price), -qty))
                    remaining -= qty
        else:
            # Buy from asks.
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if remaining <= 0:
                    break
                avol = abs(order_depth.sell_orders[ask_price])
                qty = min(avol, remaining)
                if qty > 0:
                    orders.append(Order(product, int(ask_price), qty))
                    remaining -= qty
        # Reset HWM after a flatten so subsequent re-entry is fresh.
        saved.pop("hp_tp_hwm", None)
        # Cache reason for debugging (not logged unless log_regime).
        saved["hp_last_flatten"] = (state.timestamp, flatten_reason)
        return orders

    if regime == "pinned":
        return _trade_hp_static(state, saved)
    if regime == "trending":
        mode = rp.get("trend_handler", "freeze")
        if mode == "freeze":
            # Sweep winner: emit no orders. Letting any inherited PINNED book
            # ride beats both (a) v06h's continued accumulation at fixed
            # FV=9990 (catastrophic on live d2 drop) and (b) the asymmetric
            # static_skewed handler (still bleeds on capsule false-positives).
            return []
        return _trade_hp_static_trend(state, saved)
    return _trade_hp_as_mm(state, saved)


# ── VEV_EXTRACT spot — MM around clamped EMA, tracks net voucher delta ────

def _tte_years(state: TradingState, saved: dict) -> float:
    """TTE in years, accounting for day rollovers detected during BT/live.
    
    saved['day_count'] increments each time ts drops below the last seen ts
    (i.e. a new day starts). Initial value = 0 → first day uses TTE_DAYS_LIVE.
    """
    last_ts = saved.get("last_ts", -1)
    day_count = saved.get("day_count", 0)
    if state.timestamp < last_ts:
        day_count += 1
        saved["day_count"] = day_count
    saved["last_ts"] = state.timestamp
    pv = PARAMS_VOUCHER
    days_left = pv["tte_days_live"] - day_count - state.timestamp / 1_000_000.0
    return max(days_left / 365.0, 1.0 / 365.0 / 48.0)


def _get_sigma(state: TradingState, saved: dict, S: float) -> float:
    """Return σ used for BS pricing. If auto_iv enabled, solve IV from
    ATM voucher mid each tick and EMA-smooth, with hard min/max guards.
    Falls back to PARAMS_VOUCHER['sigma_global'] on any failure.
    """
    pv = PARAMS_VOUCHER
    base = pv["sigma_global"]
    if not pv.get("auto_iv", False):
        return base
    K_atm = pv["auto_iv_strike"]
    sym = f"VEV_{K_atm}"
    od = state.order_depths.get(sym)
    if od is None:
        return saved.get("auto_sigma", base)
    bb, ba = get_best_bid_ask(od)
    if bb is None or ba is None:
        return saved.get("auto_sigma", base)
    mid = (bb + ba) / 2.0
    T = _tte_years(state, saved)
    try:
        iv = implied_vol(mid, S, float(K_atm), T, r=0.0,
                         sigma_init=saved.get("auto_sigma", base))
    except Exception:
        iv = None
    if iv is None or iv != iv:  # NaN guard
        return saved.get("auto_sigma", base)
    iv = max(pv["auto_iv_min"], min(pv["auto_iv_max"], iv))
    prev = saved.get("auto_sigma", iv)
    new = (1 - pv["auto_iv_alpha"]) * prev + pv["auto_iv_alpha"] * iv
    saved["auto_sigma"] = new
    return new


def compute_voucher_delta(state: TradingState, saved: dict, S: float) -> Tuple[float, Dict[int, float]]:
    """Aggregate Σ δ_K · pos_K and per-strike δ for hedge sizing."""
    pv = PARAMS_VOUCHER
    T = _tte_years(state, saved)
    sigma = _get_sigma(state, saved, S)
    total = 0.0
    deltas: Dict[int, float] = {}
    for K in pv["active_strikes"]:
        sym = f"VEV_{K}"
        pos = state.position.get(sym, 0)
        d = bs_call_delta(S, float(K), T, 0.0, sigma)
        deltas[K] = d
        total += d * pos
    pos_4000 = state.position.get("VEV_4000", 0)
    if pos_4000 != 0:
        total += pos_4000
    return total, deltas


def trade_vev_spot(state: TradingState, saved: dict, hedge_size: int) -> List[Order]:
    product = "VELVETFRUIT_EXTRACT"
    if product not in state.order_depths:
        return []
    p = PARAMS_VEV_SPOT
    order_depth = state.order_depths[product]
    position = state.position.get(product, 0)
    limit = LIMITS[product]

    bb, ba = get_best_bid_ask(order_depth)
    if bb is None or ba is None:
        return []
    mid = (bb + ba) / 2.0
    if "vev_fv" not in saved:
        saved["vev_fv"] = p["anchor_init"]
    saved["vev_fv"] = (1 - p["anchor_alpha"]) * saved["vev_fv"] + p["anchor_alpha"] * mid
    lo, hi = p["anchor_clamp"]
    fair = max(lo, min(hi, saved["vev_fv"]))

    orders: List[Order] = []
    buy_used = sell_used = 0
    max_buy = max(0, limit - position)
    max_sell = max(0, limit + position)

    # Phase 0: HEDGE — preempt MM if hedge_size demands
    if hedge_size > 0 and max_buy > 0:
        # need to buy spot (we are net-short delta from vouchers)
        for ask in sorted(order_depth.sell_orders.keys()):
            if hedge_size <= 0 or buy_used >= max_buy:
                break
            if ask > fair + 3:
                break
            v = abs(order_depth.sell_orders[ask])
            qty = min(v, max_buy - buy_used, hedge_size)
            if qty > 0:
                orders.append(Order(product, ask, qty))
                buy_used += qty; hedge_size -= qty
    elif hedge_size < 0 and max_sell > 0:
        for bid in sorted(order_depth.buy_orders.keys(), reverse=True):
            if hedge_size >= 0 or sell_used >= max_sell:
                break
            if bid < fair - 3:
                break
            v = abs(order_depth.buy_orders[bid])
            qty = min(v, max_sell - sell_used, -hedge_size)
            if qty > 0:
                orders.append(Order(product, bid, -qty))
                sell_used += qty; hedge_size += qty

    # Phase 0.5 (v04e): MR overlay on short EMA(N) of mid.
    # Front-run the FV-anchored TAKE when the fast deviation signals MR.
    if p.get("mr_enabled", False):
        N = max(2, int(p.get("mr_ema_window", 10)))
        alpha = 2.0 / (N + 1.0)
        if "vev_mid_ema" not in saved:
            saved["vev_mid_ema"] = mid
        else:
            saved["vev_mid_ema"] = (1 - alpha) * saved["vev_mid_ema"] + alpha * mid
        dev = mid - saved["vev_mid_ema"]
        k_thr = float(p.get("mr_k_thr", 5.0))
        mr_cap = int(p.get("mr_max_size", 10))
        if dev > k_thr and sell_used < max_sell:
            # Price rich vs MR mean → sell aggressively into bids
            mr_left = mr_cap
            for bid in sorted(order_depth.buy_orders.keys(), reverse=True):
                if mr_left <= 0 or sell_used >= max_sell:
                    break
                v = abs(order_depth.buy_orders[bid])
                qty = min(v, max_sell - sell_used, mr_left)
                if qty > 0:
                    orders.append(Order(product, bid, -qty))
                    sell_used += qty
                    mr_left -= qty
        elif dev < -k_thr and buy_used < max_buy:
            # Price cheap vs MR mean → buy aggressively from asks
            mr_left = mr_cap
            for ask in sorted(order_depth.sell_orders.keys()):
                if mr_left <= 0 or buy_used >= max_buy:
                    break
                v = abs(order_depth.sell_orders[ask])
                qty = min(v, max_buy - buy_used, mr_left)
                if qty > 0:
                    orders.append(Order(product, ask, qty))
                    buy_used += qty
                    mr_left -= qty

    # Phase 1: TAKE crossing FV
    for ask in sorted(order_depth.sell_orders.keys()):
        if ask < fair - p["take_thresh"] and buy_used < max_buy:
            v = abs(order_depth.sell_orders[ask])
            qty = min(v, max_buy - buy_used)
            if qty > 0:
                orders.append(Order(product, ask, qty)); buy_used += qty
    for bid in sorted(order_depth.buy_orders.keys(), reverse=True):
        if bid > fair + p["take_thresh"] and sell_used < max_sell:
            v = abs(order_depth.buy_orders[bid])
            qty = min(v, max_sell - sell_used)
            if qty > 0:
                orders.append(Order(product, bid, -qty)); sell_used += qty

    est = position + buy_used - sell_used

    # Phase 2: MM quotes within soft cap (DISABLED — capsule shows persistent
    # bleed from being picked off; rely on take + hedge only).
    soft_cap = int(p["soft_cap_frac"] * limit)
    fv_int = int(round(fair))
    dist = p["post_dist"]
    rem_buy = max(0, limit - est)
    rem_sell = max(0, limit + est)
    if not p.get("make_disabled", False):
        bp = max(bb + 1, fv_int - dist) if bb < fair else (fv_int - dist)
        ap = min(ba - 1, fv_int + dist) if ba > fair else (fv_int + dist)
        bp = min(bp, fv_int - 1)
        ap = max(ap, fv_int + 1)
        if est < soft_cap and rem_buy > 0:
            orders.append(Order(product, bp, min(rem_buy, soft_cap - est)))
        if est > -soft_cap and rem_sell > 0:
            orders.append(Order(product, ap, -min(rem_sell, soft_cap + est)))
    return orders


# ── v05a smile-aware voucher MM ───────────────────────────────────────────

def _solve_3x3(M: List[List[float]], y: List[float]) -> Optional[List[float]]:
    """Cramer's rule for 3x3 system. Returns None if near-singular."""
    def det3(m):
        return (m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])
              - m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])
              + m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]))
    D = det3(M)
    if abs(D) < 1e-12:
        return None
    out = []
    for col in range(3):
        Mi = [row[:] for row in M]
        for r in range(3):
            Mi[r][col] = y[r]
        out.append(det3(Mi) / D)
    return out


def _fit_smile(state: TradingState, saved: dict, S: float) -> Optional[Tuple[float, float, float]]:
    """OLS-fit parabola IV(m) = a m² + b m + c over liquid strikes; EMA-smooth.
    Returns (a, b, c) or last cached value if fit fails this tick.
    """
    pv = PARAMS_VOUCHER_V05
    T = _tte_years(state, saved)
    sqrtT = math.sqrt(max(T, 1e-9))
    pts: List[Tuple[float, float]] = []
    sigma_seed = saved.get("smile_c", 0.25)
    for K in pv["liquid_strikes"]:
        sym = f"VEV_{K}"
        od = state.order_depths.get(sym)
        if od is None:
            continue
        bb, ba = get_best_bid_ask(od)
        if bb is None or ba is None:
            continue
        mid_K = (bb + ba) / 2.0
        try:
            iv = implied_vol(mid_K, S, float(K), T, r=0.0, sigma_init=max(sigma_seed, 0.05))
        except Exception:
            iv = None
        if iv is None or iv != iv:
            continue
        if iv < pv["iv_min"] or iv > pv["iv_max"]:
            continue
        m = math.log(float(K) / S) / sqrtT
        pts.append((m, iv))
    if len(pts) < pv["min_strikes_for_fit"]:
        # Fall back to cached coefficients (stale but better than nothing)
        if "smile_a" in saved:
            return (saved["smile_a"], saved["smile_b"], saved["smile_c"])
        return None

    # OLS for [a, b, c] in y = a x² + b x + c
    n = len(pts)
    Sx = Sxx = Sxxx = Sxxxx = Sy = Sxy = Sxxy = 0.0
    for x, y in pts:
        x2 = x * x
        Sx += x; Sxx += x2; Sxxx += x2 * x; Sxxxx += x2 * x2
        Sy += y; Sxy += x * y; Sxxy += x2 * y
    M = [
        [Sxxxx, Sxxx, Sxx],
        [Sxxx,  Sxx,  Sx],
        [Sxx,   Sx,   float(n)],
    ]
    rhs = [Sxxy, Sxy, Sy]
    sol = _solve_3x3(M, rhs)
    if sol is None:
        if "smile_a" in saved:
            return (saved["smile_a"], saved["smile_b"], saved["smile_c"])
        return None
    a_new, b_new, c_new = sol
    # Sanity-clamp the level coefficient (c ≈ ATM IV)
    if not (pv["iv_min"] <= c_new <= pv["iv_max"]):
        if "smile_a" in saved:
            return (saved["smile_a"], saved["smile_b"], saved["smile_c"])
        return None

    alpha = pv["parabola_ema_alpha"]
    a_prev = saved.get("smile_a", a_new)
    b_prev = saved.get("smile_b", b_new)
    c_prev = saved.get("smile_c", c_new)
    a = (1 - alpha) * a_prev + alpha * a_new
    b = (1 - alpha) * b_prev + alpha * b_new
    c = (1 - alpha) * c_prev + alpha * c_new
    saved["smile_a"], saved["smile_b"], saved["smile_c"] = a, b, c
    return (a, b, c)


def trade_voucher_v05a(state: TradingState, saved: dict, K: int, S: float,
                       smile: Tuple[float, float, float]) -> List[Order]:
    """Smile-aware passive MM. Posts bid/ask around fair = BS(S,K,T,smileIV).
    Crosses only when book is deeply mispriced (ask < fair − edge_take)."""
    sym = f"VEV_{K}"
    if sym not in state.order_depths:
        return []
    pv = PARAMS_VOUCHER_V05
    od = state.order_depths[sym]
    pos = state.position.get(sym, 0)
    limit = LIMITS[sym]
    cap = min(limit, pv["max_pos_per_strike"])

    bb, ba = get_best_bid_ask(od)
    if bb is None or ba is None:
        return []

    T = _tte_years(state, saved)
    sqrtT = math.sqrt(max(T, 1e-9))
    a, b, c = smile
    m = math.log(float(K) / S) / sqrtT
    iv = a * m * m + b * m + c
    iv = max(pv["iv_min"], min(pv["iv_max"], iv))

    fair = bs_call_price(S, float(K), T, 0.0, iv)
    vega = bs_call_vega(S, float(K), T, 0.0, iv)
    is_dead = K in pv["dead_strikes"]
    edge = max(pv["min_edge"], vega * pv["iv_uncertainty"])
    if is_dead:
        edge *= pv["dead_edge_mult"]
    # v06g: per-K edge bump (defensive widening; stacks with dead_edge_mult)
    wmult = pv.get("wide_edge_strikes", {}).get(K)
    if wmult:
        edge *= float(wmult)
    edge_take = pv["edge_take_mult"] * edge

    # v09a Patch 1: deep-OTM absolute edge — when voucher mid < 10, override to
    # edge=1. Replaces the old K=5500-specific 0.3·spread formula. With mid≈5
    # and spread=1 the old code gave max(1,0.3)=1 but spread=7 gave 2.1 (~40%
    # of fair). The new code pins edge=1 regardless of spread.
    voucher_mid = (bb + ba) / 2.0
    if voucher_mid < 10.0:
        edge = 1.0
        edge_take = pv["edge_take_mult"] * edge
    elif K == 5500:
        # Keep old K=5500 logic for mid ≥ 10 (dead code in practice; safety net).
        spread_5500 = ba - bb
        edge = max(1.0, 0.3 * spread_5500)
        edge_take = pv["edge_take_mult"] * edge

    # v09a Patch 2 FIX (V2): floor changed from 1.0 → pv["min_edge"] (=0.1)
    # so it can't be wider than the natural vega edge (~0.775).
    if K == 5100:
        spread_5100 = ba - bb
        edge = max(pv["min_edge"], V09A_EDGE_MULT_5100 * spread_5100)
        edge_take = pv["edge_take_mult"] * edge

    # v06g: short-circuit for strikes that should contribute to the smile
    # fit (still in liquid_strikes) but never receive quotes or takes.
    if K in pv.get("skip_quote_strikes", ()):
        return []

    orders: List[Order] = []
    max_buy = max(0, cap - pos)
    max_sell = max(0, cap + pos)
    buy_used = sell_used = 0

    # TAKE only when deeply mispriced.
    for ask in sorted(od.sell_orders.keys()):
        if ask < fair - edge_take and buy_used < max_buy:
            v = abs(od.sell_orders[ask])
            qty = min(v, max_buy - buy_used)
            if qty > 0:
                orders.append(Order(sym, ask, qty)); buy_used += qty
        else:
            break
    for bid in sorted(od.buy_orders.keys(), reverse=True):
        if bid > fair + edge_take and sell_used < max_sell:
            v = abs(od.buy_orders[bid])
            qty = min(v, max_sell - sell_used)
            if qty > 0:
                orders.append(Order(sym, bid, -qty)); sell_used += qty
        else:
            break

    est = pos + buy_used - sell_used
    rem_buy = max(0, cap - est)
    rem_sell = max(0, cap + est)

    # PASSIVE quotes: never cross.
    qsize = pv["quote_size"]
    bid_px = int(math.floor(fair - edge))
    ask_px = int(math.ceil(fair + edge))
    if bid_px >= ba:
        bid_px = ba - 1
    if ask_px <= bb:
        ask_px = bb + 1
    if bid_px >= ask_px:
        # collapsed band; widen one tick each
        bid_px = min(bid_px, int(math.floor(fair)) - 1)
        ask_px = max(ask_px, int(math.ceil(fair)) + 1)
    if rem_buy > 0 and bid_px > 0 and bid_px < ba:
        orders.append(Order(sym, bid_px, min(rem_buy, qsize)))
    if rem_sell > 0 and ask_px > bb:
        orders.append(Order(sym, ask_px, -min(rem_sell, qsize)))
    return orders


# ── Vouchers (v04 legacy) — BS-MM around single σ ─────────────────────────

def trade_voucher(state: TradingState, saved: dict, K: int, S: float) -> List[Order]:
    sym = f"VEV_{K}"
    if sym not in state.order_depths:
        return []
    pv = PARAMS_VOUCHER
    order_depth = state.order_depths[sym]
    position = state.position.get(sym, 0)
    limit = LIMITS[sym]

    bb, ba = get_best_bid_ask(order_depth)
    if bb is None or ba is None:
        return []

    T = _tte_years(state, saved)
    sigma = _get_sigma(state, saved, S)
    fair = bs_call_price(S, float(K), T, 0.0, sigma)

    spread = ba - bb
    edge = max(pv["edge_floor"], pv["edge_frac"] * spread)

    orders: List[Order] = []
    max_buy = max(0, limit - position)
    max_sell = max(0, limit + position)

    # TAKE: cross-VS-fair
    buy_used = sell_used = 0
    for ask in sorted(order_depth.sell_orders.keys()):
        if ask < fair - edge and buy_used < max_buy:
            v = abs(order_depth.sell_orders[ask])
            qty = min(v, max_buy - buy_used)
            if qty > 0:
                orders.append(Order(sym, ask, qty)); buy_used += qty
    for bid in sorted(order_depth.buy_orders.keys(), reverse=True):
        if bid > fair + edge and sell_used < max_sell:
            v = abs(order_depth.buy_orders[bid])
            qty = min(v, max_sell - sell_used)
            if qty > 0:
                orders.append(Order(sym, bid, -qty)); sell_used += qty

    # SWING (jmerle template): if mid is on one side of fair±edge,
    # post heavy at fair±edge to bang to limit.
    mid = (bb + ba) / 2.0
    swing_cap = int(pv["limit_frac"] * limit)
    est = position + buy_used - sell_used
    rem_buy = max(0, limit - est)
    rem_sell = max(0, limit + est)

    if mid < fair - edge:
        # Cheap → go long
        target_bid = max(bb, int(math.floor(fair - edge)))
        target_bid = min(target_bid, int(math.floor(fair)) - 1)
        if rem_buy > 0 and target_bid > 0:
            qty = min(rem_buy, max(swing_cap - est, 0) + (rem_buy if est < 0 else 0))
            qty = min(rem_buy, qty)
            if qty > 0:
                orders.append(Order(sym, target_bid, qty))
    elif mid > fair + edge:
        # Rich → go short
        target_ask = min(ba, int(math.ceil(fair + edge)))
        target_ask = max(target_ask, int(math.ceil(fair)) + 1)
        if rem_sell > 0:
            qty = min(rem_sell, max(swing_cap + est, 0) + (rem_sell if est > 0 else 0))
            qty = min(rem_sell, qty)
            if qty > 0:
                orders.append(Order(sym, target_ask, -qty))
    else:
        # Inside band → passive MM at fair±edge if spread is wide enough
        if spread >= pv["min_strike_spread_for_make"]:
            bp = max(bb + 1, int(math.floor(fair - edge)))
            ap = min(ba - 1, int(math.ceil(fair + edge)))
            if bp < ap:
                size_each = max(1, int(swing_cap * 0.3))
                if rem_buy > 0 and bp > 0:
                    orders.append(Order(sym, bp, min(rem_buy, size_each)))
                if rem_sell > 0:
                    orders.append(Order(sym, ap, -min(rem_sell, size_each)))
    return orders


# ── v05c voucher MR overlay (additive on top of v05a quotes) ──────────────

def voucher_mr_overlay(
    state: TradingState,
    saved: dict,
    K: int,
    W: int,
    k_thr: float,
    max_size: int,
    orders: List[Order],
) -> List[Order]:
    """v05c: EMA(W) mean-reversion overlay on voucher VEV_K mid.

    ADDITIVE on top of v05a voucher orders: never reduces them, only adds
    aggressive take orders when |mid - EMA| crosses k_thr. Caps incremental
    size at max_size and respects remaining position headroom after the
    existing orders.
    """
    sym = f"VEV_{K}"
    if sym not in state.order_depths:
        return orders
    od = state.order_depths[sym]
    bb, ba = get_best_bid_ask(od)
    if bb is None or ba is None:
        return orders
    mid = (bb + ba) / 2.0

    key = f"vev_{K}_mid_ema"
    alpha = 2.0 / (W + 1.0)
    if key not in saved:
        saved[key] = mid
    else:
        saved[key] = (1 - alpha) * saved[key] + alpha * mid
    dev = mid - saved[key]

    if abs(dev) < k_thr:
        return orders

    position = state.position.get(sym, 0)
    limit = LIMITS[sym]
    buy_used = sum(o.quantity for o in orders if o.quantity > 0)
    sell_used = sum(-o.quantity for o in orders if o.quantity < 0)
    rem_buy = max(0, limit - position - buy_used)
    rem_sell = max(0, limit + position - sell_used)

    if dev >= k_thr and rem_sell > 0:
        mr_left = max_size
        for bid in sorted(od.buy_orders.keys(), reverse=True):
            if mr_left <= 0 or rem_sell <= 0:
                break
            v = abs(od.buy_orders[bid])
            qty = min(v, rem_sell, mr_left)
            if qty > 0:
                orders.append(Order(sym, bid, -qty))
                rem_sell -= qty
                mr_left -= qty
    elif dev <= -k_thr and rem_buy > 0:
        mr_left = max_size
        for ask in sorted(od.sell_orders.keys()):
            if mr_left <= 0 or rem_buy <= 0:
                break
            v = abs(od.sell_orders[ask])
            qty = min(v, rem_buy, mr_left)
            if qty > 0:
                orders.append(Order(sym, ask, qty))
                rem_buy -= qty
                mr_left -= qty
    return orders


# ── Main Trader ────────────────────────────────────────────────────────────


def _vev_5300_gate_check(
    state: TradingState,
    saved: dict,
    smile: Optional[Tuple[float, float, float]],
    counters: Dict[str, int],
) -> bool:
    """v07: regime gate for the K=5300 MR overlay.

    Updates rolling state (mid, mid-stdev, realized vol) every tick regardless
    of gate outcome, then evaluates each enabled sub-gate. Returns True iff
    every enabled sub-gate passes.
    """
    cfg = PARAMS_VEV_5300_GATE
    counters["checks"] = counters.get("checks", 0) + 1
    if not cfg.get("enabled", True):
        return False

    sym = "VEV_5300"
    od = state.order_depths.get(sym)
    if od is None:
        return False
    bb, ba = get_best_bid_ask(od)
    if bb is None or ba is None:
        return False
    mid = (bb + ba) / 2.0
    spread = ba - bb

    # Always update rolling buffers so they're warm even on gate-blocked ticks.
    hist = saved.get("vev5300_mid_hist")
    if not isinstance(hist, list):
        hist = []
    hist.append(mid)
    win = max(int(cfg.get("vmid_sigma_window", 100)),
              int(cfg.get("sigma_realized_window", 60)),
              int(PARAMS_VEV_5300_OUTLIER.get("vmid_sigma_window", 200)),
              int(PARAMS_VEV_5300_OUTLIER.get("realized_window", 200))) + 2
    if len(hist) > win:
        hist = hist[-win:]
    saved["vev5300_mid_hist"] = hist

    # tick counter (per-day reset on ts dropping)
    last_ts = saved.get("vev5300_last_ts", -1)
    if state.timestamp < last_ts:
        saved["vev5300_tick"] = 0
        saved["vev5300_day_outlier"] = False
        saved["vev5300_outlier_decided"] = False
    saved["vev5300_last_ts"] = state.timestamp
    saved["vev5300_tick"] = saved.get("vev5300_tick", 0) + 1
    tick = saved["vev5300_tick"]

    # v08 Branch B: per-day outlier detector. Decides ONCE at `detect_ticks`
    # then latches for the rest of the day; the early-vol regime is the signal.
    out_cfg = PARAMS_VEV_5300_OUTLIER
    if out_cfg.get("enabled", False):
        if not saved.get("vev5300_outlier_decided", False):
            if tick >= int(out_cfg.get("detect_ticks", 300)):
                decided = False
                if out_cfg.get("use_realized", False):
                    w = int(out_cfg.get("realized_window", 200))
                    if len(hist) >= w + 1:
                        seg = hist[-(w + 1):]
                        rets = [seg[i + 1] - seg[i] for i in range(len(seg) - 1)]
                        m = sum(rets) / len(rets)
                        var = sum((r - m) ** 2 for r in rets) / max(1, len(rets) - 1)
                        rsd = math.sqrt(max(var, 0.0))
                        if rsd > float(out_cfg.get("realized_max", 0.5)):
                            saved["vev5300_day_outlier"] = True
                        decided = True
                else:
                    w = int(out_cfg.get("vmid_sigma_window", 200))
                    if len(hist) >= max(10, w // 4):
                        seg = hist[-w:]
                        m = sum(seg) / len(seg)
                        var = sum((x - m) ** 2 for x in seg) / len(seg)
                        sd = math.sqrt(max(var, 0.0))
                        if sd > float(out_cfg.get("vmid_sigma_max", 1.5)):
                            saved["vev5300_day_outlier"] = True
                        decided = True
                if decided:
                    saved["vev5300_outlier_decided"] = True
        if saved.get("vev5300_day_outlier", False):
            counters["block_outlier"] = counters.get("block_outlier", 0) + 1
            return False

    # Gate 3: warmup
    if cfg.get("use_warmup", False):
        if tick < int(cfg.get("min_warmup_ticks", 100)):
            counters["block_warmup"] = counters.get("block_warmup", 0) + 1
            return False

    # Gate 4: spread
    if cfg.get("use_spread", False):
        if spread > int(cfg.get("max_spread_ticks", 4)):
            counters["block_spread"] = counters.get("block_spread", 0) + 1
            return False

    # Gate 2: rolling stdev of voucher mid below band
    if cfg.get("use_vmid_sigma", False):
        w = int(cfg.get("vmid_sigma_window", 100))
        if len(hist) < max(10, w // 4):
            counters["block_vmid_sigma"] = counters.get("block_vmid_sigma", 0) + 1
            return False
        seg = hist[-w:]
        m = sum(seg) / len(seg)
        var = sum((x - m) ** 2 for x in seg) / len(seg)
        sd = math.sqrt(max(var, 0.0))
        if sd > float(cfg.get("vmid_sigma_max", 1.5)):
            counters["block_vmid_sigma"] = counters.get("block_vmid_sigma", 0) + 1
            return False

    # Gate 1: realized vs implied agreement
    if cfg.get("use_realized_match", False):
        if smile is None:
            counters["block_realized"] = counters.get("block_realized", 0) + 1
            return False
        w = int(cfg.get("sigma_realized_window", 60))
        if len(hist) < w + 1:
            counters["block_realized"] = counters.get("block_realized", 0) + 1
            return False
        seg = hist[-(w + 1):]
        rets = [seg[i + 1] - seg[i] for i in range(len(seg) - 1)]
        m = sum(rets) / len(rets)
        var = sum((r - m) ** 2 for r in rets) / max(1, len(rets) - 1)
        sd_per_tick = math.sqrt(max(var, 0.0))
        # Convert smile ATM IV (annualized) to per-tick voucher-mid stdev.
        T = _tte_years(state, saved)
        # vega-style scaling: dV ≈ vega * dσ ≈ S * sqrt(T/year) * dσ (rough);
        # for a same-units comparison we instead compare *normalized* sigmas:
        # sigma_imp_per_tick ≈ smile_c * S * sqrt(T_per_tick).
        S_ema = saved.get("vev_S_ema")
        if S_ema is None:
            counters["block_realized"] = counters.get("block_realized", 0) + 1
            return False
        a, b, c = smile
        # m = log(K/S)/sqrt(T); for K=5300, evaluate IV at that m.
        sqrtT = math.sqrt(max(T, 1e-9))
        m_log = math.log(5300.0 / S_ema) / sqrtT
        iv = a * m_log * m_log + b * m_log + c
        # per-tick stdev of voucher (≈ S * iv * sqrt(dt)); dt = one tick of T.
        # T is in years, capsule ~ 10000 ticks/day, ~250 days/yr → T_tick ≈ T/2.5e6
        # but for capsule we'll just use sqrt(1/10000) of capsule-day fraction.
        dt_year = max(T, 1e-9) / 1_000_000.0
        sigma_imp_per_tick = S_ema * iv * math.sqrt(dt_year)
        if abs(sd_per_tick - sigma_imp_per_tick) > float(cfg.get("sigma_match_thresh", 0.05)) * S_ema:
            counters["block_realized"] = counters.get("block_realized", 0) + 1
            return False

    counters["passed"] = counters.get("passed", 0) + 1
    return True



class Trader:
    # v06h: shared regime counter — sweep harness reads this after each run
    # to compute per-day pinned/noisy distribution (trader_data is truncated
    # by the visualizer Logger and may drop the counts).
    HP_REGIME_COUNTS: Dict[str, int] = {"pinned": 0, "trending": 0, "noisy": 0}
    VEV_5300_GATE_COUNTS: Dict[str, int] = {
        "checks": 0, "passed": 0,
        "block_warmup": 0, "block_spread": 0,
        "block_vmid_sigma": 0, "block_realized": 0,
        "block_outlier": 0,
        "fired_buy": 0, "fired_sell": 0,
    }

    def __init__(self):
        type(self).HP_REGIME_COUNTS = {"pinned": 0, "trending": 0, "noisy": 0}
        type(self).VEV_5300_GATE_COUNTS = {
            "checks": 0, "passed": 0,
            "block_warmup": 0, "block_spread": 0,
            "block_vmid_sigma": 0, "block_realized": 0,
            "block_outlier": 0,
            "fired_buy": 0, "fired_sell": 0,
        }

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}

        try:
            saved = json.loads(state.traderData) if state.traderData else {}
        except (json.JSONDecodeError, TypeError):
            saved = {}

        # Compute spot S for vouchers/hedge from VEV_EXTRACT mid
        S: Optional[float] = None
        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            mid = get_mid_price(state.order_depths["VELVETFRUIT_EXTRACT"])
            if mid is not None:
                if "vev_S_ema" not in saved:
                    saved["vev_S_ema"] = mid
                # Light smoothing only — vouchers want a near-instant S.
                saved["vev_S_ema"] = 0.5 * saved["vev_S_ema"] + 0.5 * mid
                S = saved["vev_S_ema"]

        # Aggregate voucher delta → hedge size for spot leg
        hedge_size = 0
        if S is not None:
            try:
                D, _deltas = compute_voucher_delta(state, saved, S)
                if abs(D) > PARAMS_HEDGE["trigger"]:
                    hedge_size = -int(round(D))
            except Exception as e:
                logger.print(f"HEDGE ERR: {e}")

        # v05a: fit IV smile once per tick, before per-strike voucher trading.
        smile: Optional[Tuple[float, float, float]] = None
        if S is not None:
            try:
                smile = _fit_smile(state, saved, S)
            except Exception as e:
                logger.print(f"SMILE ERR: {e}")
                smile = None

        # Trade each product safely
        for product in state.order_depths:
            try:
                if product == "ASH_COATED_OSMIUM":
                    result[product] = trade_osmium(state, saved)
                elif product == "INTARIAN_PEPPER_ROOT":
                    result[product] = trade_pepper(state, saved)
                elif product == "HYDROGEL_PACK":
                    result[product] = trade_hydrogel(state, saved)
                elif product == "VELVETFRUIT_EXTRACT":
                    result[product] = trade_vev_spot(state, saved, hedge_size)
                elif product.startswith("VEV_"):
                    try:
                        K = int(product.split("_")[1])
                    except ValueError:
                        result[product] = []; continue
                    if S is None or smile is None:
                        result[product] = []
                    else:
                        pv5 = PARAMS_VOUCHER_V05
                        if K in pv5["enable_strikes"] or K in pv5["dead_strikes"]:
                            voucher_orders = trade_voucher_v05a(state, saved, K, S, smile)
                        else:
                            voucher_orders = []
                        # v05c: additive per-strike EMA-MR overlay (5300/5400/5500)
                        mr_cfg = PARAMS_VOUCHER_MR.get(K)
                        if mr_cfg and mr_cfg.get("enabled", False):
                            allow = True
                            if K == 5300:
                                allow = _vev_5300_gate_check(
                                    state, saved, smile,
                                    type(self).VEV_5300_GATE_COUNTS,
                                )
                            if allow:
                                before = len(voucher_orders)
                                voucher_orders = voucher_mr_overlay(
                                    state, saved, K,
                                    int(mr_cfg["W"]),
                                    float(mr_cfg["k_thr"]),
                                    int(mr_cfg["max_size"]),
                                    voucher_orders,
                                )
                                if K == 5300:
                                    for o in voucher_orders[before:]:
                                        if o.quantity > 0:
                                            type(self).VEV_5300_GATE_COUNTS["fired_buy"] = \
                                                type(self).VEV_5300_GATE_COUNTS.get("fired_buy", 0) + 1
                                        elif o.quantity < 0:
                                            type(self).VEV_5300_GATE_COUNTS["fired_sell"] = \
                                                type(self).VEV_5300_GATE_COUNTS.get("fired_sell", 0) + 1
                        # v09a Patch 3: when VEV_5300 outlier is latched, also suppress
                        # passive smile MM orders (anchor stays in liquid_strikes for fit).
                        # MR overlay already blocked by _vev_5300_gate_check; this zeroes
                        # the passive quotes posted by trade_voucher_v05a above.
                        if K == 5300 and saved.get("vev5300_day_outlier", False):
                            voucher_orders = []
                        result[product] = voucher_orders
                else:
                    result[product] = []
            except Exception as e:
                logger.print(f"{product} ERROR: {e}")
                result[product] = []

        trader_data = json.dumps(saved)
        conversions = 0
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data