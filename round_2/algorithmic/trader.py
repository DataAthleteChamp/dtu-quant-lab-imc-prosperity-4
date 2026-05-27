"""
DTU Quant Lab — IMC Prosperity 4 — Round 1 Trader
==================================================
Products: ASH_COATED_OSMIUM (pegged ~10,000), INTARIAN_PEPPER_ROOT (trend +1/tick)

Strategy:
- OSMIUM: Market-make around fixed FV=10,000 refined by micro-price (OBI signal)
  - Take mispriced orders, penny-jump passive quotes, A-S inventory skew
  - Based on Frankfurt Hedgehogs' Rainforest Resin approach + micro-price edge
- PEPPER ROOT: Trend-carry + market-making
  - FV = start_price + 0.001 * timestamp (deterministic drift)
  - Asymmetric inventory penalty (long = trend helps, short = trend hurts)
  - Maintain long bias to capture +1/tick drift

Research backing:
- Avellaneda & Stoikov (2008), Guéant/Lehalle (2012)
- Stoikov micro-price (2018), OBI correlation = +0.38
- Variance Ratio test confirms genuine mean-reversion (VR(100)=0.01)

NOTE: Self-contained for submission. No external imports beyond datamodel.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ── Logger (compressed, for jmerle visualizer) ──────────────────────────

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
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
                [state.observations.plainValueObservations, {p: [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff, o.importTariff, o.sugarPrice, o.sunlightIndex] for p, o in state.observations.conversionObservations.items()}]]

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


# ── Configuration ───────────────────────────────────────────────────────

PARAMS = {
    "ASH_COATED_OSMIUM": {
        "fair_value": 10000,
        "limit": 80,             # ← corrected: prosperity4bt/data.py LIMITS = 80
        "imb_mult": 0.0,         # disabled: A/B test showed −2.5k/day on OSMIUM (vs 0.0 baseline).
                                 # Matches R1 audit finding: "simpler is better on stable products".
                                 # Kept as tunable hook; set >0 to re-enable imbalance-nudged FV.
        "inv_skew": 0.0,         # disabled (same reason). Set to ~4.0 to re-enable inventory-skewed quotes.
        # Graduated urgent-flatten thresholds. Originally 30/38 at limit=50 (0.60/0.76 of limit).
        # Re-scaled to the same fraction of the new limit=80.
        "flatten_t1": 48,        # ≈ 0.60 × 80
        "flatten_t2": 60,        # ≈ 0.75 × 80 (tuned 61→60 via VC-sweep, +8 d-1)
    },
    "INTARIAN_PEPPER_ROOT": {
        "limit": 80,             # ← corrected: prosperity4bt/data.py LIMITS = 80
        "slope": 0.001,          # trend: +1 per tick (0.001 per timestamp unit)
    },
}


# ── Helper Functions ────────────────────────────────────────────────────

def get_best_bid_ask(order_depth: OrderDepth) -> Tuple[Optional[int], Optional[int]]:
    best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
    best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
    return best_bid, best_ask


def get_mid_price(order_depth: OrderDepth) -> Optional[float]:
    best_bid, best_ask = get_best_bid_ask(order_depth)
    if best_bid is None or best_ask is None:
        return None
    return (best_bid + best_ask) / 2.0


def get_micro_price(order_depth: OrderDepth) -> Optional[float]:
    """Stoikov (2018) micro-price: incorporates order book imbalance.
    micro = (bid * ask_vol + ask * bid_vol) / (bid_vol + ask_vol)
    """
    best_bid, best_ask = get_best_bid_ask(order_depth)
    if best_bid is None or best_ask is None:
        return None
    bid_vol = abs(order_depth.buy_orders[best_bid])
    ask_vol = abs(order_depth.sell_orders[best_ask])
    total = bid_vol + ask_vol
    if total == 0:
        return (best_bid + best_ask) / 2.0
    return (best_bid * ask_vol + best_ask * bid_vol) / total


def take_mispriced(
    product: str,
    order_depth: OrderDepth,
    fair_value: float,
    position: int,
    limit: int,
) -> Tuple[List[Order], int, int]:
    """Take any orders crossing fair value (free money). Returns orders, buy_used, sell_used."""
    orders: List[Order] = []
    max_buy = max(0, limit - position)
    max_sell = max(0, limit + position)
    buy_used = 0
    sell_used = 0

    # Buy underpriced asks
    for ask_price in sorted(order_depth.sell_orders.keys()):
        if ask_price < fair_value and buy_used < max_buy:
            ask_vol = abs(order_depth.sell_orders[ask_price])
            qty = min(ask_vol, max_buy - buy_used)
            if qty > 0:
                orders.append(Order(product, ask_price, qty))
                buy_used += qty

    # Sell overpriced bids
    for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
        if bid_price > fair_value and sell_used < max_sell:
            bid_vol = abs(order_depth.buy_orders[bid_price])
            qty = min(bid_vol, max_sell - sell_used)
            if qty > 0:
                orders.append(Order(product, bid_price, -qty))
                sell_used += qty

    return orders, buy_used, sell_used


# ── OSMIUM Strategy ────────────────────────────────────────────────────
# Proven by Frankfurt Hedgehogs (2nd global), Linear Utility (2nd global),
# CMU Physics (7th global). OSMIUM is a stable coin pegged at FV=10,000.
# ADF t=-33.71, VR(100)=0.03, Hurst=0.39, half-life=8.4 ticks.
# Strategy: Take → Flatten → Penny-jump → Post remaining.

def trade_osmium(
    state: TradingState,
    saved: dict,
) -> List[Order]:
    """Stable-coin market maker: Take→Flatten→PennyJump→Post."""
    product = "ASH_COATED_OSMIUM"
    params = PARAMS[product]
    order_depth = state.order_depths[product]
    position = state.position.get(product, 0)

    # VR5 (v6): Adaptive FV via slow EMA of mid, clamped ±3 from 10000.
    # R2 live log showed mean mid ~10004 (+4 vs R1), so fixed 10000 under-shoots R2.
    # On R1 BT: 288,388 vs 284,088 fixed-FV baseline (+4,300, every day wins).
    # Clamp ±3 prevents runaway drift if product un-pegs; EMA α=0.02 ~50-tick half-life.
    _bb_ema, _ba_ema = get_best_bid_ask(order_depth)
    if _bb_ema is not None and _ba_ema is not None:
        _mid_ema = (_bb_ema + _ba_ema) / 2.0
        if "osm_fv" not in saved:
            saved["osm_fv"] = 10000.0  # self-adapting (R2 BT showed init 10004 regresses −192)
        alpha = 0.020
        saved["osm_fv"] = (1 - alpha) * saved["osm_fv"] + alpha * _mid_ema
        fair_value_anchor = max(9997.0, min(10003.0, saved["osm_fv"]))
    else:
        fair_value_anchor = params["fair_value"]
    limit = params["limit"]
    imb_mult = params["imb_mult"]
    inv_skew = params["inv_skew"]
    flatten_t1 = params["flatten_t1"]
    flatten_t2 = params["flatten_t2"]

    # Imbalance-nudged fair value (competitor-proven edge, ~71k vs our ~18k on OSMIUM).
    # Nudge stays small (≤ ±imb_mult) so we don't drift from the 10,000 anchor.
    _bb_init, _ba_init = get_best_bid_ask(order_depth)
    _bvol = abs(order_depth.buy_orders.get(_bb_init, 0)) if _bb_init is not None else 0
    _avol = abs(order_depth.sell_orders.get(_ba_init, 0)) if _ba_init is not None else 0
    _tot_init = _bvol + _avol
    if _tot_init > 0:
        _imb = (_bvol - _avol) / _tot_init
        fair_value = fair_value_anchor + imb_mult * _imb
    else:
        fair_value = float(fair_value_anchor)

    orders: List[Order] = []
    buy_used = 0
    sell_used = 0
    max_buy = max(0, limit - position)
    max_sell = max(0, limit + position)

    # ── Phase 1: TAKE — buy below FV, sell above FV (adverse selection filter) ──
    # Skip small orders (<30 lots) within 1 tick of FV — they're often informed/toxic.
    # Deep crosses (≥2 ticks from FV) are always safe to take regardless of size.
    # Tuned 20→30 via VC11 sweep: +306 d0, ties d-2/d-1 (plateau 30-40, edge
    # only on d0 where small tagged-toxic asks exist; no loss on quieter days).
    # EARLY-TICK GATE: live R2 log analysis (334287) showed VOL=30 prevents the
    # initial OSMIUM fills (pos stays 0 for 1.9k+ ticks while 333113 had pos=6
    # by tick 100). Relax to VOL=20 for first 10k timestamps to seed inventory;
    # zero cost on R1 BT (identical 284,088), recovers R2 cold-start edge.
    ADVERSE_VOL = 20 if state.timestamp < 10000 else 30
    for ask_price in sorted(order_depth.sell_orders.keys()):
        if ask_price < fair_value and buy_used < max_buy:
            ask_vol = abs(order_depth.sell_orders[ask_price])
            if ask_vol < ADVERSE_VOL and (fair_value - ask_price) < 2:
                continue
            qty = min(ask_vol, max_buy - buy_used)
            if qty > 0:
                orders.append(Order(product, ask_price, qty))
                buy_used += qty

    for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
        if bid_price > fair_value and sell_used < max_sell:
            bid_vol = abs(order_depth.buy_orders[bid_price])
            if bid_vol < ADVERSE_VOL and (bid_price - fair_value) < 2:
                continue
            qty = min(bid_vol, max_sell - sell_used)
            if qty > 0:
                orders.append(Order(product, bid_price, -qty))
                sell_used += qty

    est_position = position + buy_used - sell_used
    remaining_buy = max(0, limit - est_position)
    remaining_sell = max(0, limit + est_position)

    # ── Safe-mode detector (Spokoiny-LPA-inspired live guard rail) ──
    # Fires ONLY on genuine outliers vs training-data envelope:
    #   training max spread = 22, max |mid-FV| = 18.5, one-sided ~2% of ticks.
    # Thresholds ~1.5x training max; one-sided books alone do NOT trigger
    # (they're in-sample), only fully empty or extreme dislocations do.
    _bb0, _ba0 = get_best_bid_ask(order_depth)
    if _bb0 is not None and _ba0 is not None:
        mid_obs = (_bb0 + _ba0) / 2.0
        spread_obs = _ba0 - _bb0
        safe_mode = spread_obs > 35 or abs(mid_obs - fair_value) > 30
    elif _bb0 is None and _ba0 is None:
        safe_mode = True
    else:
        safe_mode = False

    # ── Phase 2: FLATTEN — trade at FV to recycle position capacity ──
    # Graduated urgent flatten (validated via 50+ variant sweep on 3 days).
    # Tuned concession 5/2 → 3/1 via VC12 stacked A/B: less concession captures
    # more edge at the flatten points (+313 aggregate, every day ≥ baseline).
    # Combined with ADVERSE_VOL=30 + t2=60 gives +619 over the old baseline.
    if est_position >= flatten_t2 and not safe_mode:
        flat_sell_thresh = fair_value - 4
    elif est_position >= flatten_t1 and not safe_mode:
        flat_sell_thresh = fair_value - 1
    else:
        flat_sell_thresh = fair_value
    if est_position <= -flatten_t2 and not safe_mode:
        flat_buy_thresh = fair_value + 4
    elif est_position <= -flatten_t1 and not safe_mode:
        flat_buy_thresh = fair_value + 1
    else:
        flat_buy_thresh = fair_value
    if est_position > 0:
        # Sell at FV (or FV-1 if urgent) to reduce long exposure
        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price >= flat_sell_thresh and remaining_sell > 0:
                bid_vol = abs(order_depth.buy_orders[bid_price])
                qty = min(bid_vol, remaining_sell, est_position)
                if qty > 0:
                    orders.append(Order(product, bid_price, -qty))
                    remaining_sell -= qty
                    est_position -= qty
            else:
                break

    elif est_position < 0:
        # Buy at FV (or FV+1 if urgent) to reduce short exposure
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price <= flat_buy_thresh and remaining_buy > 0:
                ask_vol = abs(order_depth.sell_orders[ask_price])
                qty = min(ask_vol, remaining_buy, abs(est_position))
                if qty > 0:
                    orders.append(Order(product, ask_price, qty))
                    remaining_buy -= qty
                    est_position += qty
            else:
                break

    # Recalculate remaining capacity
    remaining_buy = max(0, limit - est_position)
    remaining_sell = max(0, limit + est_position)

    # ── Phase 3 & 4: PENNY-JUMP + POST ──
    # Queue-Reactive Model (Huang-Lehalle-Rosenbaum 2015, calibrated on
    # Chinese/French LOB data): when L1 queue is SHALLOW (total < 25) AND
    # queue imbalance is extreme (|QI|>=0.3), next-return prediction
    # correlation jumps from +0.59 unconditional to +0.83. We use this to
    # SHRINK posted size on the side expected to be adversely filled:
    # if bullish QR → ask will be run through → cut ask size to 30%.
    # Robust across scale∈{0.3,0.4}, QI∈{0.3,0.4,0.5}, shallow∈{20,25}.
    best_bid, best_ask = get_best_bid_ask(order_depth)
    bid_vol_best = abs(order_depth.buy_orders.get(best_bid, 0)) if best_bid is not None else 0
    ask_vol_best = abs(order_depth.sell_orders.get(best_ask, 0)) if best_ask is not None else 0
    tot_q = bid_vol_best + ask_vol_best
    qi_best = (bid_vol_best - ask_vol_best) / (tot_q + 1e-9) if tot_q > 0 else 0.0
    qr_shallow = 0 < tot_q < 25
    qr_bull = qr_shallow and qi_best >= 0.3
    qr_bear = qr_shallow and qi_best <= -0.3
    buy_scale = 0.2 if (qr_bear and not safe_mode) else 1.0
    sell_scale = 0.2 if (qr_bull and not safe_mode) else 1.0

    # ── Inventory-skewed quotes: when long, shift both bid & ask down (less eager
    # to buy more, more eager to sell). When short, mirror. Skew is proportional to
    # inventory fraction. Clamp so we never quote on the wrong side of the anchor.
    skew = int(round(inv_skew * est_position / limit))

    fv_int = int(round(fair_value_anchor))  # anchor for quote bounds (stable)
    bid_price = fv_int - 2
    ask_price = fv_int + 2
    if best_bid is not None and best_bid < fair_value:
        bid_price = min(best_bid + 1, fv_int - 1)
    if best_ask is not None and best_ask > fair_value:
        ask_price = max(best_ask - 1, fv_int + 1)

    bid_price = min(bid_price - skew, fv_int - 1)
    ask_price = max(ask_price - skew, fv_int + 1)

    if remaining_buy > 0:
        rb = int(remaining_buy * buy_scale)
        b1 = int(rb * 0.6)
        b2 = rb - b1
        if b1 > 0:
            orders.append(Order(product, bid_price, b1))
        if b2 > 0 and bid_price - 1 < fv_int:
            orders.append(Order(product, bid_price - 1, b2))
    if remaining_sell > 0:
        rs = int(remaining_sell * sell_scale)
        s1 = int(rs * 0.6)
        s2 = rs - s1
        if s1 > 0:
            orders.append(Order(product, ask_price, -s1))
        if s2 > 0 and ask_price + 1 > fv_int:
            orders.append(Order(product, ask_price + 1, -s2))

    logger.print(f"OSM: fv={fair_value:.2f} pos={position}→{est_position} b={bid_price} a={ask_price} skew={skew}")
    return orders


# ── PEPPER ROOT Strategy ───────────────────────────────────────────────

def trade_pepper(
    state: TradingState,
    saved: dict,
) -> List[Order]:
    """Trend-carry: buy to max position and HOLD. Never sell on a +1/tick trend."""
    product = "INTARIAN_PEPPER_ROOT"
    params = PARAMS[product]
    order_depth = state.order_depths[product]
    position = state.position.get(product, 0)

    limit = params["limit"]
    slope = params["slope"]

    # Determine start price for this day (persist across ticks)
    start_key = "pepper_start_price"
    mid = get_mid_price(order_depth)

    if start_key not in saved:
        if mid is not None:
            saved[start_key] = mid
        else:
            saved[start_key] = 10000

    start_price = saved[start_key]

    # Adaptive slope: if we have enough history, verify slope from data
    # Track first and latest mid for this day
    first_key = "pepper_first_mid"
    if first_key not in saved and mid is not None:
        saved[first_key] = mid

    if mid is not None and state.timestamp > 2000 and first_key in saved:
        estimated_slope = (mid - saved[first_key]) / state.timestamp
        # Only use if reasonable (between 0 and 0.005)
        if 0 <= estimated_slope <= 0.005:
            slope = estimated_slope

    # Detect day change: if price jumps significantly, reset
    if mid is not None and abs(mid - (start_price + slope * state.timestamp)) > 500:
        saved[start_key] = mid - slope * state.timestamp
        start_price = saved[start_key]
        # Reset first_mid for new day slope estimation
        saved[first_key] = mid

    # Trend fair value
    fair_trend = start_price + slope * state.timestamp

    # SAFETY: if PEPPER drift appears broken/reversed after 10k ts, force-flatten.
    # Guard against catastrophic drift reversal (~−80k/day if we hold +80 and price falls).
    # Trigger: mid has drifted DOWN >500 from start after 10k ts (expected UP by then).
    # BT cost: 0 on R1 & R2 (never triggers in normal markets).
    if mid is not None and state.timestamp > 10000 and mid < start_price - 500:
        if position > 0:
            best_bid_s, _ = get_best_bid_ask(order_depth)
            if best_bid_s is not None:
                return [Order(product, best_bid_s, -position)]
        return []

    # Refine with micro-price OBI adjustment
    micro = get_micro_price(order_depth)
    if micro is not None and mid is not None:
        obi_adj = micro - mid
        fair_value = fair_trend + obi_adj
    else:
        fair_value = fair_trend

    # Phase 1: Take any asks below fair value (cheap buys)
    orders: List[Order] = []
    buy_used = 0
    max_buy = max(0, limit - position)

    for ask_price in sorted(order_depth.sell_orders.keys()):
        if ask_price < fair_value and buy_used < max_buy:
            ask_vol = abs(order_depth.sell_orders[ask_price])
            qty = min(ask_vol, max_buy - buy_used)
            if qty > 0:
                orders.append(Order(product, ask_price, qty))
                buy_used += qty

    est_position = position + buy_used
    remaining_buy = max(0, limit - est_position)

    # Phase 1b: Aggressive buying — reach max long ASAP to capture trend.
    # Live data: selling PEPPER costs 2,283 seashells (34% of PnL).
    # Solution: buy at ANY price up to fair+10. Trend pays for overpaying.
    # 50 lots × 100 drift = 5,000 gain >> 50 lots × 10 overpay = 500 cost.
    if est_position < limit:
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price <= fair_value + 10 and remaining_buy > 0:
                ask_vol = abs(order_depth.sell_orders[ask_price])
                qty = min(ask_vol, remaining_buy)
                if qty > 0:
                    orders.append(Order(product, ask_price, qty))
                    remaining_buy -= qty
                    est_position += qty

    # Phase 2: Post remaining buy capacity at fair value (passive bid)
    # NO SELLS — on a trending product, selling = giving up future profit.
    if remaining_buy > 0:
        best_bid, best_ask = get_best_bid_ask(order_depth)
        bid_price = int(round(fair_value))
        if best_bid is not None and best_bid + 1 < fair_value:
            bid_price = max(bid_price, best_bid + 1)
        orders.append(Order(product, bid_price, remaining_buy))

    # Phase 3: SCALP-SELL — when at max long, post small passive sell 10 ticks above
    # the trend. Captures upside spikes (price oscillates around linear trend). Per-fill
    # edge = ~10 ticks × qty. Position recovers next tick via aggressive take.
    # R1 BT +383, R2 BT +603 — every day improves on both datasets.
    if est_position >= limit - 5:
        scalp_qty = min(10, est_position)
        scalp_price = int(round(fair_value)) + 10
        orders.append(Order(product, scalp_price, -scalp_qty))

    logger.print(f"PEP: fv={fair_value:.1f} trend={fair_trend:.1f} pos={position}→{est_position}")
    return orders


# ── Main Trader ─────────────────────────────────────────────────────────

class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}

        # Load persistent state
        try:
            saved = json.loads(state.traderData) if state.traderData else {}
        except (json.JSONDecodeError, TypeError):
            saved = {}

        # Trade each product
        for product in state.order_depths:
            try:
                if product == "ASH_COATED_OSMIUM":
                    result[product] = trade_osmium(state, saved)
                elif product == "INTARIAN_PEPPER_ROOT":
                    result[product] = trade_pepper(state, saved)
                else:
                    result[product] = []
            except Exception as e:
                logger.print(f"{product} ERROR: {e}")
                result[product] = []

        trader_data = json.dumps(saved)
        conversions = 0

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data