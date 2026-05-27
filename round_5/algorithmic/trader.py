import json
import math
from abc import ABC, abstractmethod
from statistics import NormalDist
from typing import Any, Dict, List, Optional, Tuple

from datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    ProsperityEncoder,
    Symbol,
    Trade,
    TradingState,
)

class Logger:
    def __init__(self) -> None:
        self.logs: str = ""
        self.max_log_length: int = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(
        self,
        state: TradingState,
        orders: dict,
        conversions: int,
        trader_data: str,
    ) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )
        max_item_length = (self.max_log_length - base_length) // 3
        print(
            self.to_json(
                [
                    self.compress_state(
                        state,
                        self.truncate(state.traderData, max_item_length),
                    ),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )
        self.logs = ""

    def compress_state(self, state: TradingState, td: str) -> list:
        return [
            state.timestamp,
            td,
            [
                [l.symbol, l.product, l.denomination]
                for l in state.listings.values()
            ],
            {
                s: [od.buy_orders, od.sell_orders]
                for s, od in state.order_depths.items()
            },
            [
                [t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                for arr in state.own_trades.values()
                for t in arr
            ],
            [
                [t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                for arr in state.market_trades.values()
                for t in arr
            ],
            state.position,
            [
                state.observations.plainValueObservations,
                {
                    p: [
                        o.bidPrice,
                        o.askPrice,
                        o.transportFees,
                        o.exportTariff,
                        o.importTariff,
                        o.sugarPrice,
                        o.sunlightIndex,
                    ]
                    for p, o in state.observations.conversionObservations.items()
                },
            ],
        ]

    def compress_orders(self, orders: dict) -> list:
        return [
            [o.symbol, o.price, o.quantity]
            for arr in orders.values()
            for o in arr
        ]

    def to_json(self, value: Any) -> str:
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

LIMITS: Dict[str, int] = {

    "PEBBLES_XS": 10,
    "PEBBLES_S": 10,
    "PEBBLES_M": 10,
    "PEBBLES_L": 10,
    "PEBBLES_XL": 10,

    "SNACKPACK_CHOCOLATE": 10,
    "SNACKPACK_PISTACHIO": 10,
    "SNACKPACK_RASPBERRY": 10,
    "SNACKPACK_STRAWBERRY": 10,
    "SNACKPACK_VANILLA": 10,

    "MICROCHIP_CIRCLE": 10,
    "MICROCHIP_OVAL": 10,
    "MICROCHIP_RECTANGLE": 10,
    "MICROCHIP_SQUARE": 10,
    "MICROCHIP_TRIANGLE": 10,

    "OXYGEN_SHAKE_CHOCOLATE": 10,
    "OXYGEN_SHAKE_EVENING_BREATH": 10,
    "OXYGEN_SHAKE_GARLIC": 10,
    "OXYGEN_SHAKE_MINT": 10,
    "OXYGEN_SHAKE_MORNING_BREATH": 10,

    "PANEL_1X2": 10,
    "PANEL_1X4": 10,
    "PANEL_2X2": 10,
    "PANEL_2X4": 10,
    "PANEL_4X4": 10,

    "UV_VISOR_AMBER": 10,
    "UV_VISOR_MAGENTA": 10,
    "UV_VISOR_ORANGE": 10,
    "UV_VISOR_RED": 10,
    "UV_VISOR_YELLOW": 10,

    "TRANSLATOR_ASTRO_BLACK": 10,
    "TRANSLATOR_ECLIPSE_CHARCOAL": 10,
    "TRANSLATOR_GRAPHITE_MIST": 10,
    "TRANSLATOR_SPACE_GRAY": 10,
    "TRANSLATOR_VOID_BLUE": 10,

    "GALAXY_SOUNDS_BLACK_HOLES": 10,
    "GALAXY_SOUNDS_DARK_MATTER": 10,
    "GALAXY_SOUNDS_PLANETARY_RINGS": 10,
    "GALAXY_SOUNDS_SOLAR_FLAMES": 10,
    "GALAXY_SOUNDS_SOLAR_WINDS": 10,

    "ROBOT_DISHES": 10,
    "ROBOT_IRONING": 10,
    "ROBOT_LAUNDRY": 10,
    "ROBOT_MOPPING": 10,
    "ROBOT_VACUUMING": 10,

    "SLEEP_POD_COTTON": 10,
    "SLEEP_POD_LAMB_WOOL": 10,
    "SLEEP_POD_NYLON": 10,
    "SLEEP_POD_POLYESTER": 10,
    "SLEEP_POD_SUEDE": 10,
}

CLUSTERS: Dict[str, List[str]] = {
    "PEBBLES": [
        "PEBBLES_XS",
        "PEBBLES_S",
        "PEBBLES_M",
        "PEBBLES_L",
        "PEBBLES_XL",
    ],
    "SNACKPACK": [
        "SNACKPACK_CHOCOLATE",
        "SNACKPACK_PISTACHIO",
        "SNACKPACK_RASPBERRY",
        "SNACKPACK_STRAWBERRY",
        "SNACKPACK_VANILLA",
    ],
    "MICROCHIP": [
        "MICROCHIP_CIRCLE",
        "MICROCHIP_OVAL",
        "MICROCHIP_RECTANGLE",
        "MICROCHIP_SQUARE",
        "MICROCHIP_TRIANGLE",
    ],
    "OXYGEN_SHAKE": [
        "OXYGEN_SHAKE_CHOCOLATE",
        "OXYGEN_SHAKE_EVENING_BREATH",
        "OXYGEN_SHAKE_GARLIC",
        "OXYGEN_SHAKE_MINT",
        "OXYGEN_SHAKE_MORNING_BREATH",
    ],
    "PANEL": [
        "PANEL_1X2",
        "PANEL_1X4",
        "PANEL_2X2",
        "PANEL_2X4",
        "PANEL_4X4",
    ],
    "UV_VISOR": [
        "UV_VISOR_AMBER",
        "UV_VISOR_MAGENTA",
        "UV_VISOR_ORANGE",
        "UV_VISOR_RED",
        "UV_VISOR_YELLOW",
    ],
    "TRANSLATOR": [
        "TRANSLATOR_ASTRO_BLACK",
        "TRANSLATOR_ECLIPSE_CHARCOAL",
        "TRANSLATOR_GRAPHITE_MIST",
        "TRANSLATOR_SPACE_GRAY",
        "TRANSLATOR_VOID_BLUE",
    ],
    "GALAXY_SOUNDS": [
        "GALAXY_SOUNDS_BLACK_HOLES",
        "GALAXY_SOUNDS_DARK_MATTER",
        "GALAXY_SOUNDS_PLANETARY_RINGS",
        "GALAXY_SOUNDS_SOLAR_FLAMES",
        "GALAXY_SOUNDS_SOLAR_WINDS",
    ],
    "ROBOT": [
        "ROBOT_DISHES",
        "ROBOT_IRONING",
        "ROBOT_LAUNDRY",
        "ROBOT_MOPPING",
        "ROBOT_VACUUMING",
    ],
    "SLEEP_POD": [
        "SLEEP_POD_COTTON",
        "SLEEP_POD_LAMB_WOOL",
        "SLEEP_POD_NYLON",
        "SLEEP_POD_POLYESTER",
        "SLEEP_POD_SUEDE",
    ],
}

PARAMS_PEBBLES: Dict[str, Any] = {

    "basket_target": 50000,

    "kill_threshold": 25.0,

    "kill_horizon": 5,

    "take_threshold": 100.0,

    "take_qty": 3,

    "make_edge": 1,

    "make_size": 8,

    "skew_qty": 0,

    "make_skew_threshold": 0.0,

    "inv_skew": 0,

    "bnp_skew": 0,
    "bnp_band": 2,

    "bnp_hard": 6,

    "dampen": 0.0,

    "max_basket_position": 5,

    "make_when_flat": 1,

    "eod_ts": 999_999_999,
}

PARAMS_SNACKPACK: Dict[str, Any] = {

    "alpha": 0.001,
    "warmup": 500,
    "z_in": 2.0,
    "z_exit": 0.3,
    "z_kill": 5.5,
    "max_pair_qty": 10,

    "rs_alpha": 0.0007,
    "rs_warmup": 500,
    "rs_z_in": 1.8,
    "rs_z_exit": 0.1,
    "rs_z_kill": 5.5,
    "max_rs_qty": 10,
    "basket_boost": 1.0,
    "hurst_gate_threshold": 99.0,
    "hurst_damp_factor": 0.5,
    "hurst_window": 40,
    "hurst_k": 4,
}

PARAMS_MICROCHIP: Dict[str, Any] = {
    "alpha_slow": 0.01,
    "z_in":  1.5,
    "z_out": 0.0,
    "qty_arb": 1,
    "warmup": 200,
    "mm_on":  True,
    "mm_qty": 3,
    "inv_skew": 1.0,
    "max_total_pos": 8,
    "use_trimmed_mean": True,
}

PARAMS_OXYGEN_SHAKE: Dict[str, Any] = {
    "alpha_slow": 0.02,
    "alpha_fast": 0.05,
    "vol_mul": 1.8,
    "z_in":  1.5,
    "z_out": 0.0,
    "qty_arb": 0,
    "warmup": 200,
    "mm_on":  True,
    "mm_qty": 3,
    "inv_skew": 1.0,
    "max_total_pos": 3,
    "use_trimmed_mean": True,
    "cb_drawdown": 2000,
    "cb_freeze":   500,
}

PARAMS_PANEL: Dict[str, Any] = {
    "alpha_slow": 0.01,
    "z_in":  1.5,
    "z_out": 0.0,
    "qty_arb": 0,
    "warmup": 200,
    "mm_on":  True,
    "mm_qty": 3,
    "inv_skew": 1.0,
    "max_total_pos": 3,
    "use_trimmed_mean": True,
    "cb_drawdown": 2000,
    "cb_freeze":   500,
}

PARAMS_UV_VISOR: Dict[str, Any] = {
    "alpha":              0.01,
    "z_in":               2.5,
    "z_out":              0.0,
    "qty_arb":            0,
    "warmup":             50,
    "mm_on":              True,
    "mm_qty":             3,
    "inv_skew":           1.0,
    "max_total_pos":      5,
    "use_trimmed_mean":   True,
    "neutral_mm":         True,
    "skip_symbols":       ["UV_VISOR_ORANGE", "UV_VISOR_YELLOW",
                           "UV_VISOR_MAGENTA", "UV_VISOR_RED"],
    "regime_alpha":       0.1,
    "regime_sigma_gate":  7.5,
    "regime_warmup":      30,
    "cb_drawdown":        1500.0,
    "cb_window":          200,
    "cb_freeze":          500,
}

PARAMS_TRANSLATOR: Dict[str, Any] = {
    "pair_alpha":  0.005,
    "pair_warmup": 99999,
    "pair_z_in":   2.0,
    "pair_z_exit": 0.3,
    "pair_z_kill": 5.5,
    "pair_qty":    2,
    "alpha":       0.01,
    "z_in":        2.5,
    "z_out":       0.0,
    "sec_qty_arb": 0,
    "warmup": 50,
    "mm_on":  True,
    "mm_qty": 2,
    "inv_skew": 1.0,
    "max_total_pos": 5,
    "use_trimmed_mean": True,
    "neutral_mm": True,
    "skip_symbols": ["TRANSLATOR_SPACE_GRAY"],
    "regime_alpha":      0.1,
    "regime_sigma_gate": 8.0,
    "regime_warmup":     30,
    "cb_drawdown": 1500.0,
    "cb_window":   200,
    "cb_freeze":   500,
}

PARAMS_GALAXY_SOUNDS: Dict[str, Any] = {
    "alpha_slow": 0.002,
    "z_in":  1.5,
    "z_out": 0.0,
    "qty_arb": 0,
    "warmup": 300,
    "mm_on":  True,
    "mm_qty": 3,
    "inv_skew": 1.0,
    "max_total_pos": 2,
    "use_trimmed_mean": True,
    "cb_window_dd":     1500,
    "cb_window_ticks":  100,
    "cb_freeze":        500,
    "cb_drawdown": 3000,
}

PARAMS_ROBOT: Dict[str, Any] = {
    "alpha_slow": 0.005,
    "z_in":  1.5,
    "z_out": 0.0,
    "qty_arb": 0,
    "warmup": 200,
    "mm_on":  True,
    "mm_qty": 3,
    "inv_skew": 1.0,
    "max_total_pos": 3,
    "use_trimmed_mean": True,
    "dishes_disabled": True,
    "cb_drawdown": 1000,
    "cb_freeze":   500,
}

PARAMS_SLEEP_POD: Dict[str, Any] = {
    "alpha_slow": 0.001,
    "alpha_fast": 0.02,
    "vol_mul": 1.8,
    "z_in":  1.5,
    "z_out": 0.0,
    "qty_arb": 0,
    "warmup": 400,
    "mm_on":  True,
    "mm_qty": 2,
    "inv_skew": 1.0,
    "max_total_pos": 2,
    "use_trimmed_mean": True,
    "cb_drawdown": 500,
    "cb_freeze":   500,
    "cb_window_dd":    500,
    "cb_window_ticks": 100,
}

_CLUSTER_PARAMS: Dict[str, Dict[str, Any]] = {
    "PEBBLES": PARAMS_PEBBLES,
    "SNACKPACK": PARAMS_SNACKPACK,
    "MICROCHIP": PARAMS_MICROCHIP,
    "OXYGEN_SHAKE": PARAMS_OXYGEN_SHAKE,
    "PANEL": PARAMS_PANEL,
    "UV_VISOR": PARAMS_UV_VISOR,
    "TRANSLATOR": PARAMS_TRANSLATOR,
    "GALAXY_SOUNDS": PARAMS_GALAXY_SOUNDS,
    "ROBOT": PARAMS_ROBOT,
    "SLEEP_POD": PARAMS_SLEEP_POD,
}


PARAMS_A_UV_VISOR: Dict[str, Any] = {
    "skip": {"UV_VISOR_AMBER"},
    "mr_beta": {},
    "half_spread": 1,
    "skew_at_limit": 4.0,
}
PARAMS_A_TRANSLATOR: Dict[str, Any] = {
    "skip": {"TRANSLATOR_SPACE_GRAY"},
    "mr_beta": {},
    "half_spread": 1,
    "skew_at_limit": 4.0,
}
PARAMS_A_SLEEP_POD: Dict[str, Any] = {
    "skip": set(),
    "mr_beta": {},
    "half_spread": 1,
    "skew_at_limit": 4.0,
}
PARAMS_A_OXYGEN_SHAKE: Dict[str, Any] = {
    "skip": set(),
    "mr_beta": {
        "OXYGEN_SHAKE_EVENING_BREATH": 0.140,
        "OXYGEN_SHAKE_CHOCOLATE": 0.150,
    },
    "half_spread": 1,
    "skew_at_limit": 4.0,
}

class ClusterStrategy(ABC):
    """
    Abstract base for per-cluster strategies.

    Subclasses override update() to return orders for their cluster members.
    The returned dict must already respect the per-product order budget:
        aggregate BUY  qty <= LIMITS[symbol] - max(0,  position[symbol])
        aggregate SELL qty <= LIMITS[symbol] - max(0, -position[symbol])
    Master Trader performs a final defensive clip after merging all clusters.
    """

    def __init__(
        self,
        cluster_name: str,
        members: List[str],
        params: Dict[str, Any],
        limits: Dict[str, int],
    ) -> None:
        self.cluster_name = cluster_name
        self.members = members
        self.params = params
        self.limits = limits
        self.state_data: Dict[str, Any] = {}

    def load_state(self, saved: Dict[str, Any]) -> None:
        """Restore per-cluster state from traderData."""
        self.state_data = dict(saved) if saved else {}

    def dump_state(self) -> Dict[str, Any]:
        """Serialise per-cluster state into traderData."""
        return dict(self.state_data)

    @abstractmethod
    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        """
        Compute orders for all cluster members for this tick.
        Returns an empty dict in the skeleton; Phase C subclasses override this.
        """
        ...

class SkeletonClusterStrategy(ClusterStrategy):
    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        return {}


class AStyleMMStrategy(ClusterStrategy):
    """
    Plain wall-mid MM with position skew + optional lag-1 MR overlay.

    Ports A (563030)'s standard MM logic into B's ClusterStrategy framework.
    Live D5 evidence: this style beats B's elaborate strategies on UV_VISOR
    (+11.3k swing), TRANSLATOR (+10.8k), SLEEP_POD (+3.8k), OXYGEN_SHAKE (+0.8k).

    Params:
      skip: set of products to NOT trade (structural drift / momentum).
      mr_beta: dict of product -> beta, applies lag-1 MR overlay to FV.
      half_spread: ticks beyond fair value for passive quote.
      skew_at_limit: position-skew tick magnitude at full inventory limit.
    """

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        skip: set = self.params.get("skip", set())
        mr_beta: Dict[str, float] = self.params.get("mr_beta", {})
        half_spread: int = int(self.params.get("half_spread", 1))
        skew_at_limit: float = float(self.params.get("skew_at_limit", 4.0))
        prev_mids: Dict[str, float] = self.state_data.get("prev_mids", {}) or {}

        result: Dict[Symbol, List[Order]] = {}
        cur_mids: Dict[str, float] = {}
        for product in self.members:
            if product in skip:
                result[product] = []
                continue
            od = state.order_depths.get(product)
            if od is None:
                result[product] = []
                continue
            mid = self._wall_mid(od)
            if mid is None:
                result[product] = []
                continue
            cur_mids[product] = mid
            position = state.position.get(product, 0) if state.position else 0

            beta = mr_beta.get(product, 0.0)
            last_mid = prev_mids.get(product)
            if beta > 0.0 and last_mid is not None:
                last_ret = mid - last_mid
                fv = mid - beta * last_ret
            else:
                fv = mid

            result[product] = self._trade_mm(product, od, position, fv,
                                              half_spread, skew_at_limit)

        # Persist mids for next tick's MR signal
        merged_prev = dict(prev_mids)
        for p, m in cur_mids.items():
            merged_prev[p] = m
        self.state_data["prev_mids"] = merged_prev
        return result

    @staticmethod
    def _wall_mid(od: OrderDepth) -> Optional[float]:
        bids = od.buy_orders
        asks = od.sell_orders
        if not bids and not asks:
            return None
        if not bids:
            return min(asks) - 0.5
        if not asks:
            return max(bids) + 0.5
        if len(bids) >= 2 and len(asks) >= 2:
            return (min(bids) + max(asks)) / 2.0
        return (max(bids) + min(asks)) / 2.0

    def _trade_mm(self, product: str, od: OrderDepth, position: int, fv: float,
                  half_spread: int, skew_at_limit: float) -> List[Order]:
        limit = self.limits.get(product, 10)
        orders: List[Order] = []
        max_buy = max(0, limit - position)
        max_sell = max(0, limit + position)
        bb = max(od.buy_orders) if od.buy_orders else None
        ba = min(od.sell_orders) if od.sell_orders else None

        for ask_price in sorted(od.sell_orders.keys()):
            if max_buy <= 0:
                break
            if ask_price < fv:
                qty = min(abs(od.sell_orders[ask_price]), max_buy)
                if qty > 0:
                    orders.append(Order(product, ask_price, qty))
                    max_buy -= qty
            else:
                break
        for bid_price in sorted(od.buy_orders.keys(), reverse=True):
            if max_sell <= 0:
                break
            if bid_price > fv:
                qty = min(abs(od.buy_orders[bid_price]), max_sell)
                if qty > 0:
                    orders.append(Order(product, bid_price, -qty))
                    max_sell -= qty
            else:
                break

        skew = (position / float(limit)) * skew_at_limit
        quote_buy = fv - half_spread - skew
        quote_sell = fv + half_spread - skew
        bid_price = int(math.floor(quote_buy))
        ask_price = int(math.ceil(quote_sell))
        if bb is not None:
            bid_price = min(bid_price, bb + 1)
        if ba is not None:
            ask_price = max(ask_price, ba - 1)
        if bb is not None and ask_price <= bb:
            ask_price = bb + 1
        if ba is not None and bid_price >= ba:
            bid_price = ba - 1
        if bid_price >= ask_price:
            ask_price = bid_price + 1

        if max_buy > 0:
            orders.append(Order(product, bid_price, max_buy))
        if max_sell > 0:
            orders.append(Order(product, ask_price, -max_sell))
        return orders

class PebblesBasketArb(ClusterStrategy):
    """
    PEBBLES is a near-deterministic basket: sum of mids ≈ 50,000 with σ ≈ 2.8.
    Strategy:
      (1) PASSIVE MAKE on each leg around the touch, with skew driven by basket_residual.
      (2) AGGRESSIVE TAKE when |basket_residual| crosses take_threshold.
      (3) HARD KILL flatten if |residual| > kill_threshold (regime-break sentinel).
    All sizing respects the per-product position cap = 10 (pre-match BT enforcement).
    """

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        p = self.params
        if not p:
            return {}
        members = self.members
        depths = state.order_depths
        position = state.position or {}

        bids: Dict[str, int] = {}
        asks: Dict[str, int] = {}
        bid_qtys: Dict[str, int] = {}
        ask_qtys: Dict[str, int] = {}
        mids: Dict[str, float] = {}
        for leg in members:
            od = depths.get(leg)
            if od is None or not od.buy_orders or not od.sell_orders:
                return {}
            bb = max(od.buy_orders.keys())
            ba = min(od.sell_orders.keys())
            if ba <= bb:
                return {}
            bids[leg] = int(bb)
            asks[leg] = int(ba)
            bid_qtys[leg] = int(od.buy_orders[bb])
            ask_qtys[leg] = int(-od.sell_orders[ba])
            mids[leg] = (bb + ba) / 2.0

        residual = sum(mids.values()) - float(p["basket_target"])
        abs_res = abs(residual)

        kill_remaining = int(self.state_data.get("kr", 0))
        if abs_res > float(p["kill_threshold"]):
            kill_remaining = max(kill_remaining, int(p["kill_horizon"]))
        if kill_remaining > 0:
            self.state_data["kr"] = kill_remaining - 1
            return self._flatten(members, position)
        else:
            self.state_data["kr"] = 0

        dampen = float(p.get("dampen", 0.0))
        max_bp = int(p.get("max_basket_position", 0))
        if dampen > 0.0 and max_bp > 0:
            tbp = int(round(-residual / dampen))
            if tbp > max_bp:
                tbp = max_bp
            elif tbp < -max_bp:
                tbp = -max_bp
        else:
            tbp = 0

        take_thr = float(p["take_threshold"])
        take_qty = int(p["take_qty"])
        make_edge = int(p["make_edge"])
        make_size = int(p["make_size"])
        skew_qty = int(p.get("skew_qty", 0))
        skew_thr = float(p.get("make_skew_threshold", 0.0))
        inv_skew = int(p.get("inv_skew", 0))
        make_when_flat = bool(p.get("make_when_flat", 1))
        bnp_skew = int(p.get("bnp_skew", 0))
        bnp_band = int(p.get("bnp_band", 2))
        bnp_hard = int(p.get("bnp_hard", 6))
        eod_ts = int(p.get("eod_ts", 10**12))

        basket_pos = sum(int(position.get(leg, 0)) for leg in members)

        if int(state.timestamp) >= eod_ts:
            return self._flatten(members, position)

        orders: Dict[str, List[Order]] = {leg: [] for leg in members}

        for leg in members:
            pos = int(position.get(leg, 0))
            limit = int(self.limits[leg])
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)
            bb = bids[leg]
            ba = asks[leg]

            if abs_res >= take_thr:
                if residual > 0:

                    qty = min(take_qty, bid_qtys[leg], cap_sell)
                    if qty > 0:
                        orders[leg].append(Order(leg, bb, -qty))
                        cap_sell -= qty
                else:
                    qty = min(take_qty, ask_qtys[leg], cap_buy)
                    if qty > 0:
                        orders[leg].append(Order(leg, ba, qty))
                        cap_buy -= qty

                if residual > 0 and cap_buy > 0:
                    bx = bb + make_edge
                    if bx < ba:
                        orders[leg].append(Order(leg, bx, min(make_size, cap_buy)))
                elif residual < 0 and cap_sell > 0:
                    sx = ba - make_edge
                    if sx > bb:
                        orders[leg].append(Order(leg, sx, -min(make_size, cap_sell)))
                continue

            buy_qty = make_size
            sell_qty = make_size

            if residual > skew_thr:

                sell_qty += skew_qty
                buy_qty = max(0, buy_qty - skew_qty)
            elif residual < -skew_thr:
                buy_qty += skew_qty
                sell_qty = max(0, sell_qty - skew_qty)
            elif not make_when_flat:
                buy_qty = 0
                sell_qty = 0

            if inv_skew > 0:
                if pos > 0:
                    sell_qty += inv_skew
                    buy_qty = max(0, buy_qty - inv_skew)
                elif pos < 0:
                    buy_qty += inv_skew
                    sell_qty = max(0, sell_qty - inv_skew)

            if bnp_skew > 0 and abs(basket_pos) > bnp_band:
                if basket_pos > 0:
                    if abs(basket_pos) > bnp_hard:
                        buy_qty = 0
                        sell_qty += bnp_skew
                    else:
                        buy_qty = max(0, buy_qty - bnp_skew)
                        sell_qty += bnp_skew
                else:
                    if abs(basket_pos) > bnp_hard:
                        sell_qty = 0
                        buy_qty += bnp_skew
                    else:
                        sell_qty = max(0, sell_qty - bnp_skew)
                        buy_qty += bnp_skew

            if dampen > 0.0:
                want_delta = tbp - pos
                if want_delta > 0:
                    buy_qty += min(want_delta, 2)
                elif want_delta < 0:
                    sell_qty += min(-want_delta, 2)

            buy_qty = max(0, min(buy_qty, cap_buy))
            sell_qty = max(0, min(sell_qty, cap_sell))

            buy_px = bb + make_edge
            sell_px = ba - make_edge

            if buy_px >= sell_px:
                buy_px = bb
                sell_px = ba

            if buy_qty > 0:
                orders[leg].append(Order(leg, buy_px, buy_qty))
            if sell_qty > 0:
                orders[leg].append(Order(leg, sell_px, -sell_qty))

        return orders

    def _flatten(
        self, members: List[str], position: Dict[str, int]
    ) -> Dict[Symbol, List[Order]]:
        """Emit IOC-style orders to flatten any non-zero leg position via a wide
        cross.  Used when the kill switch is armed.  Each side is sized so the
        per-product cap can never be breached even if all orders fill."""
        out: Dict[str, List[Order]] = {}
        for leg in members:
            pos = int(position.get(leg, 0))
            if pos > 0:
                out[leg] = [Order(leg, 1, -pos)]
            elif pos < 0:
                out[leg] = [Order(leg, 1_000_000, -pos)]
        return out

class SnackpackPairMR(ClusterStrategy):
    """Mean-reversion pair trader for the SNACKPACK cluster (CHOC-VAN, RASP-STRAW)."""

    CHOC = "SNACKPACK_CHOCOLATE"
    VAN = "SNACKPACK_VANILLA"
    RASP = "SNACKPACK_RASPBERRY"
    STRAW = "SNACKPACK_STRAWBERRY"
    PIST = "SNACKPACK_PISTACHIO"

    def _mid(self, state: TradingState, sym: str) -> Optional[float]:
        od = state.order_depths.get(sym)
        if not od or not od.buy_orders or not od.sell_orders:
            return None
        return (max(od.buy_orders) + min(od.sell_orders)) / 2.0

    def _best_ba(
        self, state: TradingState, sym: str
    ) -> Tuple[Optional[int], Optional[int]]:
        od = state.order_depths.get(sym)
        if not od or not od.buy_orders or not od.sell_orders:
            return None, None
        return max(od.buy_orders), min(od.sell_orders)

    def _ema_update(
        self, old_mu: float, old_sq: float, val: float, alpha: float
    ) -> Tuple[float, float]:
        new_mu = old_mu * (1.0 - alpha) + val * alpha
        new_sq = old_sq * (1.0 - alpha) + val * val * alpha
        return new_mu, new_sq

    def _z_score(self, val: float, mu: float, sq: float, min_std: float = 1.0) -> float:
        var = max(sq - mu * mu, min_std * min_std)
        return (val - mu) / math.sqrt(var)

    def _variance_ratio(self, hist: List[float], k: int) -> float:
        n = len(hist)
        if n < k + 2:
            return 1.0
        d1 = [hist[i + 1] - hist[i] for i in range(n - 1)]
        dk = [hist[i + k] - hist[i] for i in range(n - k)]
        mean1 = sum(d1) / len(d1)
        meank = sum(dk) / len(dk)
        var1 = sum((x - mean1) ** 2 for x in d1) / len(d1)
        vark = sum((x - meank) ** 2 for x in dk) / len(dk)
        if var1 < 1e-9:
            return 1.0
        return vark / (k * var1)

    def _hurst_size_factor(self, hist: List[float]) -> float:
        threshold = self.params.get("hurst_gate_threshold", 99.0)
        damp = self.params.get("hurst_damp_factor", 0.5)
        k = self.params.get("hurst_k", 4)
        vr = self._variance_ratio(hist, k)
        if vr > threshold:
            return damp
        return 1.0

    def _trade_pair(
        self,
        state: TradingState,
        sym_a: str,
        sym_b: str,
        z: float,
        z_in: float,
        z_exit: float,
        z_kill: float,
        max_qty: int,
        size_factor: float,
    ) -> Dict[str, List[Order]]:
        pos_a = state.position.get(sym_a, 0)
        pos_b = state.position.get(sym_b, 0)
        lim = self.limits.get(sym_a, 10)

        bid_a, ask_a = self._best_ba(state, sym_a)
        bid_b, ask_b = self._best_ba(state, sym_b)
        if bid_a is None or bid_b is None:
            return {}

        effective_qty = max(1, round(max_qty * size_factor))

        if abs(z) > z_kill:
            desired = 0
        elif pos_a == 0:
            if z > z_in:
                desired = -effective_qty
            elif z < -z_in:
                desired = effective_qty
            else:
                return {}
        elif pos_a > 0:
            if z > -z_exit:
                desired = 0
            else:
                return {}
        else:
            if z < z_exit:
                desired = 0
            else:
                return {}

        delta = desired - pos_a
        if delta == 0:
            return {}

        orders: Dict[str, List[Order]] = {}
        if delta > 0:
            cap_buy_a = lim - max(0, pos_a)
            cap_sell_b = lim - max(0, -pos_b)
            qty = min(delta, cap_buy_a, cap_sell_b)
            if qty > 0:
                orders[sym_a] = [Order(sym_a, ask_a, qty)]
                orders[sym_b] = [Order(sym_b, bid_b, -qty)]
        else:
            qty = -delta
            cap_sell_a = lim - max(0, -pos_a)
            cap_buy_b = lim - max(0, pos_b)
            qty = min(qty, cap_sell_a, cap_buy_b)
            if qty > 0:
                orders[sym_a] = [Order(sym_a, bid_a, -qty)]
                orders[sym_b] = [Order(sym_b, ask_b, qty)]

        return orders

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        result: Dict[str, List[Order]] = {}

        p = self.params
        if not p:
            return result
        alpha = p["alpha"]
        warmup = p["warmup"]

        mids: Dict[str, float] = {}
        for sym in self.members:
            m = self._mid(state, sym)
            if m is not None:
                mids[sym] = m

        n = self.state_data.get("n", 0)

        cv_mu = self.state_data.get("cv_mu", 0.0)
        cv_sq = self.state_data.get("cv_sq", 0.0)
        hist_cv: List[float] = self.state_data.get("hist_cv", [])

        cv_ok = self.CHOC in mids and self.VAN in mids
        if cv_ok:
            spread_cv = mids[self.CHOC] - mids[self.VAN]
            if n == 0:
                cv_mu = spread_cv
                cv_sq = spread_cv * spread_cv
            else:
                cv_mu, cv_sq = self._ema_update(cv_mu, cv_sq, spread_cv, alpha)
            hist_cv.append(spread_cv)
            hw = p.get("hurst_window", 40)
            if len(hist_cv) > hw:
                hist_cv = hist_cv[-hw:]

        rs_mu = self.state_data.get("rs_mu", 0.0)
        rs_sq = self.state_data.get("rs_sq", 0.0)
        rs_alpha = p.get("rs_alpha", alpha)

        rs_ok = self.RASP in mids and self.STRAW in mids
        if rs_ok:
            spread_rs = mids[self.RASP] - mids[self.STRAW]
            if n == 0:
                rs_mu = spread_rs
                rs_sq = spread_rs * spread_rs
            else:
                rs_mu, rs_sq = self._ema_update(rs_mu, rs_sq, spread_rs, rs_alpha)

        bk_mu = self.state_data.get("bk_mu", 50000.0)
        if len(mids) == 5:
            basket = sum(mids.values())
            bk_mu = bk_mu * (1 - alpha) + basket * alpha

        self.state_data["n"] = n + 1
        self.state_data["cv_mu"] = cv_mu
        self.state_data["cv_sq"] = cv_sq
        self.state_data["rs_mu"] = rs_mu
        self.state_data["rs_sq"] = rs_sq
        self.state_data["bk_mu"] = bk_mu
        self.state_data["hist_cv"] = [int(x) for x in hist_cv]

        if n < warmup:
            return result

        z_in = p["z_in"]
        z_exit = p["z_exit"]
        z_kill = p["z_kill"]

        basket_boost = p.get("basket_boost", 1.0)
        boost_factor = 1.0
        if basket_boost > 1.0 and cv_ok and len(mids) == 5:
            basket = sum(mids.values())
            bk_residual = basket - bk_mu
            spread_cv_cur = mids[self.CHOC] - mids[self.VAN]
            z_cv_cur = self._z_score(spread_cv_cur, cv_mu, cv_sq)
            if z_cv_cur > 0 and bk_residual > 0:
                boost_factor = basket_boost
            elif z_cv_cur < 0 and bk_residual < 0:
                boost_factor = basket_boost
            else:
                boost_factor = 1.0 / basket_boost

        if cv_ok:
            spread_cv = mids[self.CHOC] - mids[self.VAN]
            z_cv = self._z_score(spread_cv, cv_mu, cv_sq)
            hurst_factor = self._hurst_size_factor(hist_cv)
            size_factor = boost_factor * hurst_factor
            cv_orders = self._trade_pair(
                state, self.CHOC, self.VAN,
                z_cv, z_in, z_exit, z_kill,
                p["max_pair_qty"], size_factor,
            )
            for sym, ords in cv_orders.items():
                result.setdefault(sym, []).extend(ords)

        max_rs = p.get("max_rs_qty", 0)
        if max_rs > 0 and rs_ok:
            rs_warmup = p.get("rs_warmup", warmup)
            rs_z_in = p.get("rs_z_in", z_in)
            rs_z_exit = p.get("rs_z_exit", z_exit)
            rs_z_kill = p.get("rs_z_kill", z_kill)
            if n >= rs_warmup:
                spread_rs = mids[self.RASP] - mids[self.STRAW]
                z_rs = self._z_score(spread_rs, rs_mu, rs_sq)
                rs_orders = self._trade_pair(
                    state, self.RASP, self.STRAW,
                    z_rs, rs_z_in, rs_z_exit, rs_z_kill,
                    max_rs, 1.0,
                )
                for sym, ords in rs_orders.items():
                    result.setdefault(sym, []).extend(ords)

        return result

_MEMBERS_MICROCHIP = [
    "MICROCHIP_CIRCLE",
    "MICROCHIP_OVAL",
    "MICROCHIP_RECTANGLE",
    "MICROCHIP_SQUARE",
    "MICROCHIP_TRIANGLE",
]
_N_MICROCHIP = len(_MEMBERS_MICROCHIP)

class MicrochipPCAResid(ClusterStrategy):
    """Trimmed-mean basket-deviation z-score MR + inside-spread MM."""

    def _init_state(self) -> None:
        self.state_data = {
            "sd": [0.0] * _N_MICROCHIP,
            "sd2": [1.0] * _N_MICROCHIP,
            "ticks": 0,
        }

    def load_state(self, saved: Dict[str, Any]) -> None:
        if not saved:
            self._init_state()
            return
        try:
            self.state_data = {
                "sd": list(saved["sd"]),
                "sd2": list(saved["sd2"]),
                "ticks": int(saved["ticks"]),
            }
        except (KeyError, TypeError):
            self._init_state()

    def dump_state(self) -> Dict[str, Any]:
        if not self.state_data:
            self._init_state()
        return {
            "sd": [round(x, 6) for x in self.state_data["sd"]],
            "sd2": [round(x, 6) for x in self.state_data["sd2"]],
            "ticks": self.state_data["ticks"],
        }

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        if not self.state_data:
            self._init_state()
        p = self.params
        if not p:
            return {}
        alpha = p["alpha_slow"]
        z_in = p["z_in"]
        z_out = p["z_out"]
        qty_arb = p["qty_arb"]
        warmup = p["warmup"]
        mm_on = p["mm_on"]
        mm_qty = p["mm_qty"]
        inv_skew = p["inv_skew"]
        max_total = p["max_total_pos"]
        use_trim = p.get("use_trimmed_mean", True)

        sd = self.state_data["sd"]
        sd2 = self.state_data["sd2"]
        self.state_data["ticks"] += 1
        ticks = self.state_data["ticks"]

        pos_map = state.position if state.position else {}

        mids: List[Optional[float]] = []
        bbs: List[Optional[int]] = []
        bas: List[Optional[int]] = []

        for sym in _MEMBERS_MICROCHIP:
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                mids.append(None); bbs.append(None); bas.append(None)
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            mids.append((bb + ba) / 2.0)
            bbs.append(bb)
            bas.append(ba)

        valid = [m for m in mids if m is not None]
        if len(valid) < 3:
            return {}

        if use_trim and len(valid) >= 3:
            sv = sorted(valid)
            basket_mean = sum(sv[1:-1]) / (len(sv) - 2)
        else:
            basket_mean = sum(valid) / len(valid)

        zs: List[Optional[float]] = []
        for i in range(_N_MICROCHIP):
            m = mids[i]
            if m is None:
                zs.append(None); continue
            dev = m - basket_mean
            sd[i] = (1.0 - alpha) * sd[i] + alpha * dev
            sd2[i] = (1.0 - alpha) * sd2[i] + alpha * dev * dev
            var = max(1e-8, sd2[i] - sd[i] * sd[i])
            zs.append((dev - sd[i]) / math.sqrt(var))

        if ticks < warmup:
            return {}

        result: Dict[Symbol, List[Order]] = {}

        for i, sym in enumerate(_MEMBERS_MICROCHIP):
            if bbs[i] is None or bas[i] is None:
                continue
            bb = bbs[i]
            ba = bas[i]
            z = zs[i]
            pos = pos_map.get(sym, 0)
            limit = self.limits.get(sym, 10)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)

            skew = int(round(pos * inv_skew))
            buy_px = bb + 1 - max(0, skew)
            sell_px = ba - 1 - min(0, skew)
            buy_px = max(bb + 1, min(ba - 2, buy_px))
            sell_px = min(ba - 1, max(bb + 2, sell_px))

            buy_qty = mm_qty if mm_on else 0
            sell_qty = mm_qty if mm_on else 0

            if z is not None:
                if z < -z_in and pos < max_total:
                    buy_qty += qty_arb
                elif z > z_in and pos > -max_total:
                    sell_qty += qty_arb
                elif abs(z) < z_out:
                    if pos > 0:
                        sell_qty += min(pos, max_total)
                    elif pos < 0:
                        buy_qty += min(-pos, max_total)

            if pos >= max_total:
                buy_qty = 0
            if pos <= -max_total:
                sell_qty = 0

            buy_qty = max(0, min(buy_qty, cap_buy))
            sell_qty = max(0, min(sell_qty, cap_sell))

            orders: List[Order] = []
            if buy_qty > 0: orders.append(Order(sym, int(buy_px), buy_qty))
            if sell_qty > 0: orders.append(Order(sym, int(sell_px), -sell_qty))

            tb = sum(o.quantity for o in orders if o.quantity > 0)
            ts = sum(-o.quantity for o in orders if o.quantity < 0)
            if tb > cap_buy or ts > cap_sell:
                continue

            if orders:
                result[sym] = orders

        return result

_MEMBERS_UV_VISOR = [
    "UV_VISOR_AMBER",
    "UV_VISOR_MAGENTA",
    "UV_VISOR_ORANGE",
    "UV_VISOR_RED",
    "UV_VISOR_YELLOW",
]
_N_UV_VISOR = len(_MEMBERS_UV_VISOR)

class UVVisorStrategy(ClusterStrategy):
    """Trimmed-mean basket-deviation z-score MR + neutral inside-spread MM with regime gate + CB."""

    def _init_state(self) -> None:
        self.state_data = {
            "sd": [0.0] * _N_UV_VISOR,
            "sd2": [1.0] * _N_UV_VISOR,
            "bv": 0.0,
            "bv2": 0.0,
            "prev_bs": None,
            "ticks": 0,
            "freeze_until": 0,
            "peak_mtm": 0.0,
            "peak_reset": 0,
        }

    def load_state(self, saved: Dict[str, Any]) -> None:
        if not saved:
            self._init_state()
            return
        try:
            self.state_data = {
                "sd": list(saved["sd"]),
                "sd2": list(saved["sd2"]),
                "bv": float(saved.get("bv", 0.0)),
                "bv2": float(saved.get("bv2", 0.0)),
                "prev_bs": saved.get("prev_bs"),
                "ticks": int(saved["ticks"]),
                "freeze_until": int(saved.get("freeze_until", 0)),
                "peak_mtm": float(saved.get("peak_mtm", 0.0)),
                "peak_reset": int(saved.get("peak_reset", 0)),
            }
        except (KeyError, TypeError):
            self._init_state()

    def dump_state(self) -> Dict[str, Any]:
        if not self.state_data:
            self._init_state()
        s = self.state_data
        return {
            "sd": [round(x, 6) for x in s["sd"]],
            "sd2": [round(x, 6) for x in s["sd2"]],
            "bv": round(s["bv"], 4),
            "bv2": round(s["bv2"], 4),
            "prev_bs": s.get("prev_bs"),
            "ticks": s["ticks"],
            "freeze_until": s["freeze_until"],
            "peak_mtm": round(s["peak_mtm"], 2),
            "peak_reset": s["peak_reset"],
        }

    def _mtm(self, state: TradingState, pos_map: Dict[str, int]) -> float:
        total = 0.0
        for sym in _MEMBERS_UV_VISOR:
            pos = pos_map.get(sym, 0)
            if pos == 0:
                continue
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                continue
            mid = (max(od.buy_orders) + min(od.sell_orders)) / 2.0
            total += pos * mid
        return total

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        if not self.state_data:
            self._init_state()
        p = self.params
        if not p:
            return {}
        alpha = p["alpha"]
        z_in = p["z_in"]
        z_out = p["z_out"]
        qty_arb = p["qty_arb"]
        warmup = p["warmup"]
        mm_on = p["mm_on"]
        mm_qty = p["mm_qty"]
        inv_skew = p["inv_skew"]
        max_total = p["max_total_pos"]
        use_trim = p.get("use_trimmed_mean", True)
        r_alpha = p.get("regime_alpha", 0.1)
        r_gate = p.get("regime_sigma_gate", 7.5)
        r_wu = p.get("regime_warmup", 30)
        cb_dd = p.get("cb_drawdown", 1500.0)
        cb_win = p.get("cb_window", 200)
        cb_frz = p.get("cb_freeze", 500)
        skip_syms = set(p.get("skip_symbols", []))
        neutral_mm = p.get("neutral_mm", False)

        sd = self.state_data["sd"]
        sd2 = self.state_data["sd2"]
        self.state_data["ticks"] += 1
        ticks = self.state_data["ticks"]

        pos_map = state.position if state.position else {}

        mids: List[Optional[float]] = []
        bbs: List[Optional[int]] = []
        bas: List[Optional[int]] = []

        for sym in _MEMBERS_UV_VISOR:
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                mids.append(None); bbs.append(None); bas.append(None)
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            mids.append((bb + ba) / 2.0)
            bbs.append(bb)
            bas.append(ba)

        valid = [m for m in mids if m is not None]
        if len(valid) < 3:
            return {}

        if use_trim and len(valid) >= 3:
            sv = sorted(valid)
            basket_mean = sum(sv[1:-1]) / (len(sv) - 2)
        else:
            basket_mean = sum(valid) / len(valid)

        basket_avg = sum(valid) / len(valid)

        bv = self.state_data["bv"]
        bv2 = self.state_data["bv2"]
        prev_bs = self.state_data.get("prev_bs")
        if prev_bs is not None:
            bc = basket_avg - prev_bs
            bv = (1.0 - r_alpha) * bv + r_alpha * bc
            bv2 = (1.0 - r_alpha) * bv2 + r_alpha * bc * bc
        basket_sigma = math.sqrt(max(0.0, bv2 - bv * bv))
        self.state_data["bv"] = bv
        self.state_data["bv2"] = bv2
        self.state_data["prev_bs"] = basket_avg
        regime_factor = (0.5 if basket_sigma > r_gate else 1.0) if ticks >= r_wu else 1.0

        zs: List[Optional[float]] = []
        for i in range(_N_UV_VISOR):
            m = mids[i]
            if m is None:
                zs.append(None); continue
            dev = m - basket_mean
            sd[i] = (1.0 - alpha) * sd[i] + alpha * dev
            sd2[i] = (1.0 - alpha) * sd2[i] + alpha * dev * dev
            var = max(1e-8, sd2[i] - sd[i] * sd[i])
            zs.append((dev - sd[i]) / math.sqrt(var))

        mtm = self._mtm(state, pos_map)
        if (ticks - self.state_data["peak_reset"]) >= cb_win:
            self.state_data["peak_mtm"] = mtm
            self.state_data["peak_reset"] = ticks
        peak = self.state_data["peak_mtm"]
        if mtm > peak:
            self.state_data["peak_mtm"] = mtm
            peak = mtm
        if (peak - mtm) > cb_dd and ticks > warmup:
            self.state_data["freeze_until"] = ticks + cb_frz

        if ticks < warmup or ticks < self.state_data["freeze_until"]:
            return {}

        result: Dict[Symbol, List[Order]] = {}

        for i, sym in enumerate(_MEMBERS_UV_VISOR):
            if sym in skip_syms:
                continue
            if bbs[i] is None or bas[i] is None:
                continue
            bb = bbs[i]
            ba = bas[i]
            z = zs[i]
            pos = pos_map.get(sym, 0)
            limit = self.limits.get(sym, 10)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)

            skew = int(round(pos * inv_skew))
            buy_px = max(bb + 1, min(ba - 2, bb + 1 - max(0, skew)))
            sell_px = min(ba - 1, max(bb + 2, ba - 1 - min(0, skew)))

            eff_mm = max(1, round(mm_qty * regime_factor)) if mm_on else 0
            eff_arb = max(0, round(qty_arb * regime_factor))

            buy_qty = eff_mm
            sell_qty = eff_mm

            if neutral_mm:
                if pos > 0: buy_qty = 0
                if pos < 0: sell_qty = 0

            if z is not None:
                if z < -z_in and pos < max_total:
                    buy_qty += eff_arb
                elif z > z_in and pos > -max_total:
                    sell_qty += eff_arb
                elif abs(z) < z_out:
                    if pos > 0: sell_qty += min(pos, max_total)
                    elif pos < 0: buy_qty += min(-pos, max_total)

            if pos >= max_total: buy_qty = 0
            if pos <= -max_total: sell_qty = 0

            buy_qty = max(0, min(buy_qty, cap_buy))
            sell_qty = max(0, min(sell_qty, cap_sell))

            orders: List[Order] = []
            if buy_qty > 0: orders.append(Order(sym, int(buy_px), buy_qty))
            if sell_qty > 0: orders.append(Order(sym, int(sell_px), -sell_qty))

            tb = sum(o.quantity for o in orders if o.quantity > 0)
            ts = sum(-o.quantity for o in orders if o.quantity < 0)
            if tb > cap_buy or ts > cap_sell:
                continue

            if orders:
                result[sym] = orders

        return result

_MEMBERS_TRANSLATOR = [
    "TRANSLATOR_ASTRO_BLACK",
    "TRANSLATOR_ECLIPSE_CHARCOAL",
    "TRANSLATOR_GRAPHITE_MIST",
    "TRANSLATOR_SPACE_GRAY",
    "TRANSLATOR_VOID_BLUE",
]
_TR_ASTRO = "TRANSLATOR_ASTRO_BLACK"
_TR_ECLIPSE = "TRANSLATOR_ECLIPSE_CHARCOAL"
_TR_GRAPHITE = "TRANSLATOR_GRAPHITE_MIST"
_TR_SGRAY = "TRANSLATOR_SPACE_GRAY"
_TR_VOID = "TRANSLATOR_VOID_BLUE"
_IDX_TRANSLATOR = {sym: i for i, sym in enumerate(_MEMBERS_TRANSLATOR)}
_N_TRANSLATOR = len(_MEMBERS_TRANSLATOR)
_SEC_LEGS_TRANSLATOR = [_TR_ECLIPSE, _TR_SGRAY, _TR_VOID]

class TranslatorStrategy(ClusterStrategy):
    """ASTRO-GRAPHITE pair MR + per-leg residual MR + inside-spread MM with regime gate + CB."""

    def _init_state(self) -> None:
        self.state_data = {
            "ag_mu": 0.0,
            "ag_sq": 0.0,
            "sd": [0.0] * _N_TRANSLATOR,
            "sd2": [1.0] * _N_TRANSLATOR,
            "bv": 0.0,
            "bv2": 0.0,
            "prev_bs": None,
            "ticks": 0,
            "freeze_until": 0,
            "peak_mtm": 0.0,
            "peak_reset": 0,
        }

    def load_state(self, saved: Dict[str, Any]) -> None:
        if not saved:
            self._init_state()
            return
        try:
            self.state_data = {
                "ag_mu": float(saved.get("ag_mu", 0.0)),
                "ag_sq": float(saved.get("ag_sq", 0.0)),
                "sd": list(saved["sd"]),
                "sd2": list(saved["sd2"]),
                "bv": float(saved.get("bv", 0.0)),
                "bv2": float(saved.get("bv2", 0.0)),
                "prev_bs": saved.get("prev_bs"),
                "ticks": int(saved["ticks"]),
                "freeze_until": int(saved.get("freeze_until", 0)),
                "peak_mtm": float(saved.get("peak_mtm", 0.0)),
                "peak_reset": int(saved.get("peak_reset", 0)),
            }
        except (KeyError, TypeError):
            self._init_state()

    def dump_state(self) -> Dict[str, Any]:
        if not self.state_data:
            self._init_state()
        s = self.state_data
        return {
            "ag_mu": round(s["ag_mu"], 6),
            "ag_sq": round(s["ag_sq"], 6),
            "sd": [round(x, 6) for x in s["sd"]],
            "sd2": [round(x, 6) for x in s["sd2"]],
            "bv": round(s["bv"], 4),
            "bv2": round(s["bv2"], 4),
            "prev_bs": s.get("prev_bs"),
            "ticks": s["ticks"],
            "freeze_until": s["freeze_until"],
            "peak_mtm": round(s["peak_mtm"], 2),
            "peak_reset": s["peak_reset"],
        }

    def _best_ba(
        self, state: TradingState, sym: str
    ) -> Tuple[Optional[int], Optional[int]]:
        od = state.order_depths.get(sym)
        if od is None or not od.buy_orders or not od.sell_orders:
            return None, None
        return max(od.buy_orders), min(od.sell_orders)

    def _mid(self, state: TradingState, sym: str) -> Optional[float]:
        bb, ba = self._best_ba(state, sym)
        if bb is None or ba is None:
            return None
        return (bb + ba) / 2.0

    def _mtm(self, state: TradingState, pos_map: Dict[str, int]) -> float:
        total = 0.0
        for sym in _MEMBERS_TRANSLATOR:
            pos = pos_map.get(sym, 0)
            if pos == 0:
                continue
            m = self._mid(state, sym)
            if m is not None:
                total += pos * m
        return total

    def _trade_pair(
        self,
        state: TradingState,
        z: float,
        p: Dict[str, Any],
        regime_factor: float,
        pos_map: Dict[str, int],
    ) -> Dict[str, List[Order]]:
        z_in = p["pair_z_in"]
        z_exit = p["pair_z_exit"]
        z_kill = p["pair_z_kill"]
        max_qty = p["pair_qty"]

        pos_a = pos_map.get(_TR_ASTRO, 0)
        pos_b = pos_map.get(_TR_GRAPHITE, 0)
        lim = self.limits.get(_TR_ASTRO, 10)

        bid_a, ask_a = self._best_ba(state, _TR_ASTRO)
        bid_b, ask_b = self._best_ba(state, _TR_GRAPHITE)
        if bid_a is None or bid_b is None:
            return {}

        eff_qty = max(1, round(max_qty * regime_factor))

        if abs(z) > z_kill:
            desired = 0
        elif pos_a == 0:
            if z > z_in: desired = -eff_qty
            elif z < -z_in: desired = eff_qty
            else: return {}
        elif pos_a > 0:
            if z > -z_exit: desired = 0
            else: return {}
        else:
            if z < z_exit: desired = 0
            else: return {}

        delta = desired - pos_a
        if delta == 0:
            return {}

        orders: Dict[str, List[Order]] = {}
        if delta > 0:
            cap_buy_a = lim - max(0, pos_a)
            cap_sell_b = lim - max(0, -pos_b)
            qty = min(delta, cap_buy_a, cap_sell_b)
            if qty > 0:
                orders[_TR_ASTRO] = [Order(_TR_ASTRO, ask_a, qty)]
                orders[_TR_GRAPHITE] = [Order(_TR_GRAPHITE, bid_b, -qty)]
        else:
            qty = -delta
            cap_sell_a = lim - max(0, -pos_a)
            cap_buy_b = lim - max(0, pos_b)
            qty = min(qty, cap_sell_a, cap_buy_b)
            if qty > 0:
                orders[_TR_ASTRO] = [Order(_TR_ASTRO, bid_a, -qty)]
                orders[_TR_GRAPHITE] = [Order(_TR_GRAPHITE, ask_b, qty)]

        return orders

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        if not self.state_data:
            self._init_state()
        p = self.params
        if not p:
            return {}
        p_alpha = p["pair_alpha"]
        p_warmup = p["pair_warmup"]
        alpha = p["alpha"]
        z_in = p["z_in"]
        z_out = p["z_out"]
        sec_arb = p["sec_qty_arb"]
        warmup = p["warmup"]
        mm_on = p["mm_on"]
        mm_qty = p["mm_qty"]
        inv_skew = p["inv_skew"]
        max_total = p["max_total_pos"]
        use_trim = p.get("use_trimmed_mean", True)
        r_alpha = p.get("regime_alpha", 0.1)
        r_gate = p.get("regime_sigma_gate", 8.0)
        r_wu = p.get("regime_warmup", 30)
        cb_dd = p.get("cb_drawdown", 1500.0)
        cb_win = p.get("cb_window", 200)
        cb_frz = p.get("cb_freeze", 500)
        skip_syms = set(p.get("skip_symbols", []))
        neutral_mm = p.get("neutral_mm", False)

        sd = self.state_data["sd"]
        sd2 = self.state_data["sd2"]
        self.state_data["ticks"] += 1
        ticks = self.state_data["ticks"]

        pos_map = state.position if state.position else {}

        mids: List[Optional[float]] = []
        bbs: List[Optional[int]] = []
        bas: List[Optional[int]] = []

        for sym in _MEMBERS_TRANSLATOR:
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                mids.append(None); bbs.append(None); bas.append(None)
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            mids.append((bb + ba) / 2.0)
            bbs.append(bb)
            bas.append(ba)

        valid = [m for m in mids if m is not None]
        if len(valid) < 3:
            return {}

        if use_trim and len(valid) >= 3:
            sv = sorted(valid)
            basket_mean = sum(sv[1:-1]) / (len(sv) - 2)
        else:
            basket_mean = sum(valid) / len(valid)

        basket_avg = sum(valid) / len(valid)

        bv = self.state_data["bv"]
        bv2 = self.state_data["bv2"]
        prev_bs = self.state_data.get("prev_bs")
        if prev_bs is not None:
            bc = basket_avg - prev_bs
            bv = (1.0 - r_alpha) * bv + r_alpha * bc
            bv2 = (1.0 - r_alpha) * bv2 + r_alpha * bc * bc
        basket_sigma = math.sqrt(max(0.0, bv2 - bv * bv))
        self.state_data["bv"] = bv
        self.state_data["bv2"] = bv2
        self.state_data["prev_bs"] = basket_avg
        regime_factor = (0.5 if basket_sigma > r_gate else 1.0) if ticks >= r_wu else 1.0

        mid_a = mids[_IDX_TRANSLATOR[_TR_ASTRO]]
        mid_g = mids[_IDX_TRANSLATOR[_TR_GRAPHITE]]
        ag_mu = self.state_data["ag_mu"]
        ag_sq = self.state_data["ag_sq"]
        pair_ok = mid_a is not None and mid_g is not None
        spread_ag = 0.0
        if pair_ok:
            spread_ag = mid_a - mid_g
            if ticks == 1:
                ag_mu = spread_ag
                ag_sq = spread_ag * spread_ag
            else:
                ag_mu = (1.0 - p_alpha) * ag_mu + p_alpha * spread_ag
                ag_sq = (1.0 - p_alpha) * ag_sq + p_alpha * spread_ag * spread_ag
            self.state_data["ag_mu"] = ag_mu
            self.state_data["ag_sq"] = ag_sq

        zs: List[Optional[float]] = []
        for i in range(_N_TRANSLATOR):
            m = mids[i]
            if m is None:
                zs.append(None); continue
            dev = m - basket_mean
            sd[i] = (1.0 - alpha) * sd[i] + alpha * dev
            sd2[i] = (1.0 - alpha) * sd2[i] + alpha * dev * dev
            var = max(1e-8, sd2[i] - sd[i] * sd[i])
            zs.append((dev - sd[i]) / math.sqrt(var))

        mtm = self._mtm(state, pos_map)
        if (ticks - self.state_data["peak_reset"]) >= cb_win:
            self.state_data["peak_mtm"] = mtm
            self.state_data["peak_reset"] = ticks
        peak = self.state_data["peak_mtm"]
        if mtm > peak:
            self.state_data["peak_mtm"] = mtm
            peak = mtm
        if (peak - mtm) > cb_dd and ticks > warmup:
            self.state_data["freeze_until"] = ticks + cb_frz

        if ticks < warmup or ticks < self.state_data["freeze_until"]:
            return {}

        result: Dict[Symbol, List[Order]] = {}

        if pair_ok and ticks >= p_warmup:
            var_ag = max(1.0, ag_sq - ag_mu * ag_mu)
            z_ag = (spread_ag - ag_mu) / math.sqrt(var_ag)
            pair_orders = self._trade_pair(state, z_ag, p, regime_factor, pos_map)
            for sym, ords in pair_orders.items():
                result.setdefault(sym, []).extend(ords)

        for i, sym in enumerate(_MEMBERS_TRANSLATOR):
            if sym in skip_syms:
                continue
            if bbs[i] is None or bas[i] is None:
                continue
            bb = bbs[i]
            ba = bas[i]
            z = zs[i]
            pos = pos_map.get(sym, 0)
            limit = self.limits.get(sym, 10)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)

            skew = int(round(pos * inv_skew))
            buy_px = max(bb + 1, min(ba - 2, bb + 1 - max(0, skew)))
            sell_px = min(ba - 1, max(bb + 2, ba - 1 - min(0, skew)))

            eff_mm_qty = max(1, round(mm_qty * regime_factor)) if mm_on else 0

            buy_qty = eff_mm_qty
            sell_qty = eff_mm_qty

            if neutral_mm:
                if pos > 0: buy_qty = 0
                if pos < 0: sell_qty = 0

            if sym in _SEC_LEGS_TRANSLATOR and z is not None:
                eff_sec = max(0, round(sec_arb * regime_factor))
                if z < -z_in and pos < max_total:
                    buy_qty += eff_sec
                elif z > z_in and pos > -max_total:
                    sell_qty += eff_sec
                elif abs(z) < z_out:
                    if pos > 0: sell_qty += min(pos, max_total)
                    elif pos < 0: buy_qty += min(-pos, max_total)

            if pos >= max_total: buy_qty = 0
            if pos <= -max_total: sell_qty = 0

            existing = result.get(sym, [])
            existing_buy = sum(o.quantity for o in existing if o.quantity > 0)
            existing_sell = sum(-o.quantity for o in existing if o.quantity < 0)
            buy_qty = max(0, min(buy_qty, cap_buy - existing_buy))
            sell_qty = max(0, min(sell_qty, cap_sell - existing_sell))

            extra: List[Order] = []
            if buy_qty > 0: extra.append(Order(sym, int(buy_px), buy_qty))
            if sell_qty > 0: extra.append(Order(sym, int(sell_px), -sell_qty))

            if extra:
                result.setdefault(sym, []).extend(extra)

        return result

_MEMBERS_OXYGEN_SHAKE = [
    "OXYGEN_SHAKE_CHOCOLATE",
    "OXYGEN_SHAKE_EVENING_BREATH",
    "OXYGEN_SHAKE_GARLIC",
    "OXYGEN_SHAKE_MINT",
    "OXYGEN_SHAKE_MORNING_BREATH",
]
_N_OXYGEN_SHAKE = len(_MEMBERS_OXYGEN_SHAKE)

class OxygenShakeStrategy(ClusterStrategy):
    """Drift-aware trimmed-mean basket-residual MR + inside-spread MM with vol guard + CB."""

    def _init_state(self) -> None:
        self.state_data = {
            "sd": [0.0] * _N_OXYGEN_SHAKE,
            "sd2": [1.0] * _N_OXYGEN_SHAKE,
            "ticks": 0,
            "pm": [0] * _N_OXYGEN_SHAKE,
            "cm": 0.0,
            "hwm": 0.0,
            "fr": 0,
            "bf": 0.0,
            "bs": 0.0,
        }

    def load_state(self, saved: Dict[str, Any]) -> None:
        if not saved:
            self._init_state(); return
        try:
            self.state_data = {
                "sd": list(saved["sd"]),
                "sd2": list(saved["sd2"]),
                "ticks": int(saved["ticks"]),
                "pm": list(saved.get("pm", [0] * _N_OXYGEN_SHAKE)),
                "cm": float(saved.get("cm", 0.0)),
                "hwm": float(saved.get("hwm", 0.0)),
                "fr": int(saved.get("fr", 0)),
                "bf": float(saved.get("bf", 0.0)),
                "bs": float(saved.get("bs", 0.0)),
            }
        except (KeyError, TypeError):
            self._init_state()

    def dump_state(self) -> Dict[str, Any]:
        if not self.state_data:
            self._init_state()
        s = self.state_data
        return {
            "sd": [round(x, 5) for x in s["sd"]],
            "sd2": [round(x, 5) for x in s["sd2"]],
            "ticks": s["ticks"],
            "pm": [int(x) for x in s["pm"]],
            "cm": round(s["cm"], 2),
            "hwm": round(s["hwm"], 2),
            "fr": s["fr"],
            "bf": round(s["bf"], 3),
            "bs": round(s["bs"], 3),
        }

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        if not self.state_data:
            self._init_state()
        p = self.params
        if not p:
            return {}
        alpha = p["alpha_slow"]
        alpha_fast = p.get("alpha_fast", 0.05)
        vol_mul = p.get("vol_mul", 1.8)
        z_in = p["z_in"]
        z_out = p["z_out"]
        qty_arb = p["qty_arb"]
        warmup = p["warmup"]
        mm_on = p["mm_on"]
        mm_qty = p["mm_qty"]
        inv_skew = p["inv_skew"]
        max_total = p["max_total_pos"]
        use_trim = p.get("use_trimmed_mean", True)
        cb_dd = p.get("cb_drawdown", 2000)
        cb_freeze = p.get("cb_freeze", 500)

        s = self.state_data
        sd = s["sd"]
        sd2 = s["sd2"]
        s["ticks"] += 1
        ticks = s["ticks"]

        pos_map = state.position if state.position else {}

        mids: List[Optional[float]] = []
        bbs: List[Optional[int]] = []
        bas: List[Optional[int]] = []

        for sym in _MEMBERS_OXYGEN_SHAKE:
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                mids.append(None); bbs.append(None); bas.append(None)
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            mids.append((bb + ba) / 2.0)
            bbs.append(bb); bas.append(ba)

        valid = [m for m in mids if m is not None]
        if len(valid) < 3:
            return {}

        if use_trim and len(valid) >= 3:
            sv = sorted(valid)
            basket_mean = sum(sv[1:-1]) / (len(sv) - 2)
        else:
            basket_mean = sum(valid) / len(valid)

        basket_residual = abs(sum(valid) / len(valid) - basket_mean)
        s["bf"] = (1 - alpha_fast) * s["bf"] + alpha_fast * basket_residual
        s["bs"] = (1 - alpha) * s["bs"] + alpha * basket_residual
        vol_stressed = (s["bs"] > 1.0) and (s["bf"] > vol_mul * s["bs"])
        arb_scale = 0.5 if vol_stressed else 1.0

        pm = s["pm"]
        mtm_delta = 0.0
        for i in range(_N_OXYGEN_SHAKE):
            mid_i = mids[i]
            if mid_i is not None and pm[i] != 0:
                pos_i = pos_map.get(_MEMBERS_OXYGEN_SHAKE[i], 0)
                mtm_delta += pos_i * (mid_i - pm[i])
            if mid_i is not None:
                pm[i] = int(mid_i)

        s["cm"] += mtm_delta
        s["hwm"] = max(s["hwm"], s["cm"])
        if s["cm"] < s["hwm"] - cb_dd:
            s["fr"] = ticks + cb_freeze
            s["hwm"] = s["cm"]
        frozen = ticks < s["fr"]

        zs: List[Optional[float]] = []
        for i in range(_N_OXYGEN_SHAKE):
            m = mids[i]
            if m is None:
                zs.append(None); continue
            dev = m - basket_mean
            sd[i] = (1.0 - alpha) * sd[i] + alpha * dev
            sd2[i] = (1.0 - alpha) * sd2[i] + alpha * dev * dev
            var = max(1e-8, sd2[i] - sd[i] * sd[i])
            zs.append((dev - sd[i]) / math.sqrt(var))

        if ticks < warmup or frozen:
            return {}

        result: Dict[Symbol, List[Order]] = {}

        for i, sym in enumerate(_MEMBERS_OXYGEN_SHAKE):
            if bbs[i] is None or bas[i] is None:
                continue
            bb = bbs[i]
            ba = bas[i]
            z = zs[i]
            pos = pos_map.get(sym, 0)
            limit = self.limits.get(sym, 10)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)

            skew = int(round(pos * inv_skew))
            buy_px = bb + 1 - max(0, skew)
            sell_px = ba - 1 - min(0, skew)
            buy_px = max(bb + 1, min(ba - 2, buy_px))
            sell_px = min(ba - 1, max(bb + 2, sell_px))

            buy_qty = mm_qty if mm_on else 0
            sell_qty = mm_qty if mm_on else 0

            if z is not None:
                scaled_arb = max(1, int(round(qty_arb * arb_scale)))
                if z < -z_in and pos < max_total:
                    buy_qty += scaled_arb
                elif z > z_in and pos > -max_total:
                    sell_qty += scaled_arb
                elif z_out > 0 and abs(z) < z_out:
                    if pos > 0: sell_qty += min(pos, max_total)
                    elif pos < 0: buy_qty += min(-pos, max_total)

            if pos >= max_total: buy_qty = 0
            if pos <= -max_total: sell_qty = 0

            buy_qty = max(0, min(buy_qty, cap_buy))
            sell_qty = max(0, min(sell_qty, cap_sell))

            orders: List[Order] = []
            if buy_qty > 0: orders.append(Order(sym, int(buy_px), buy_qty))
            if sell_qty > 0: orders.append(Order(sym, int(sell_px), -sell_qty))

            tb = sum(o.quantity for o in orders if o.quantity > 0)
            ts = sum(-o.quantity for o in orders if o.quantity < 0)
            if tb > cap_buy or ts > cap_sell:
                continue

            if orders:
                result[sym] = orders

        return result

_MEMBERS_PANEL = [
    "PANEL_1X2",
    "PANEL_1X4",
    "PANEL_2X2",
    "PANEL_2X4",
    "PANEL_4X4",
]
_N_PANEL = len(_MEMBERS_PANEL)

class PanelStrategy(ClusterStrategy):
    """Trimmed-mean basket-residual MR + inside-spread MM for PANEL cluster."""

    def _init_state(self) -> None:
        self.state_data = {
            "sd": [0.0] * _N_PANEL,
            "sd2": [1.0] * _N_PANEL,
            "ticks": 0,
            "pm": [0] * _N_PANEL,
            "cm": 0.0,
            "hwm": 0.0,
            "fr": 0,
        }

    def load_state(self, saved: Dict[str, Any]) -> None:
        if not saved:
            self._init_state(); return
        try:
            self.state_data = {
                "sd": list(saved["sd"]),
                "sd2": list(saved["sd2"]),
                "ticks": int(saved["ticks"]),
                "pm": list(saved.get("pm", [0] * _N_PANEL)),
                "cm": float(saved.get("cm", 0.0)),
                "hwm": float(saved.get("hwm", 0.0)),
                "fr": int(saved.get("fr", 0)),
            }
        except (KeyError, TypeError):
            self._init_state()

    def dump_state(self) -> Dict[str, Any]:
        if not self.state_data:
            self._init_state()
        s = self.state_data
        return {
            "sd": [round(x, 5) for x in s["sd"]],
            "sd2": [round(x, 5) for x in s["sd2"]],
            "ticks": s["ticks"],
            "pm": [int(x) for x in s["pm"]],
            "cm": round(s["cm"], 2),
            "hwm": round(s["hwm"], 2),
            "fr": s["fr"],
        }

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        if not self.state_data:
            self._init_state()
        p = self.params
        if not p:
            return {}
        alpha = p["alpha_slow"]
        z_in = p["z_in"]
        z_out = p["z_out"]
        qty_arb = p["qty_arb"]
        warmup = p["warmup"]
        mm_on = p["mm_on"]
        mm_qty = p["mm_qty"]
        inv_skew = p["inv_skew"]
        max_total = p["max_total_pos"]
        use_trim = p.get("use_trimmed_mean", True)
        cb_dd = p.get("cb_drawdown", 2000)
        cb_freeze = p.get("cb_freeze", 500)

        s = self.state_data
        sd = s["sd"]
        sd2 = s["sd2"]
        s["ticks"] += 1
        ticks = s["ticks"]

        pos_map = state.position if state.position else {}

        mids: List[Optional[float]] = []
        bbs: List[Optional[int]] = []
        bas: List[Optional[int]] = []

        for sym in _MEMBERS_PANEL:
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                mids.append(None); bbs.append(None); bas.append(None)
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            mids.append((bb + ba) / 2.0)
            bbs.append(bb); bas.append(ba)

        valid = [m for m in mids if m is not None]
        if len(valid) < 3:
            return {}

        if use_trim and len(valid) >= 3:
            sv = sorted(valid)
            basket_mean = sum(sv[1:-1]) / (len(sv) - 2)
        else:
            basket_mean = sum(valid) / len(valid)

        pm = s["pm"]
        mtm_delta = 0.0
        for i in range(_N_PANEL):
            mid_i = mids[i]
            if mid_i is not None and pm[i] != 0:
                pos_i = pos_map.get(_MEMBERS_PANEL[i], 0)
                mtm_delta += pos_i * (mid_i - pm[i])
            if mid_i is not None:
                pm[i] = int(mid_i)

        s["cm"] += mtm_delta
        s["hwm"] = max(s["hwm"], s["cm"])
        if s["cm"] < s["hwm"] - cb_dd:
            s["fr"] = ticks + cb_freeze
            s["hwm"] = s["cm"]
        frozen = ticks < s["fr"]

        zs: List[Optional[float]] = []
        for i in range(_N_PANEL):
            m = mids[i]
            if m is None:
                zs.append(None); continue
            dev = m - basket_mean
            sd[i] = (1.0 - alpha) * sd[i] + alpha * dev
            sd2[i] = (1.0 - alpha) * sd2[i] + alpha * dev * dev
            var = max(1e-8, sd2[i] - sd[i] * sd[i])
            zs.append((dev - sd[i]) / math.sqrt(var))

        if ticks < warmup or frozen:
            return {}

        result: Dict[Symbol, List[Order]] = {}

        for i, sym in enumerate(_MEMBERS_PANEL):
            if bbs[i] is None or bas[i] is None:
                continue
            bb = bbs[i]
            ba = bas[i]
            z = zs[i]
            pos = pos_map.get(sym, 0)
            limit = self.limits.get(sym, 10)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)

            skew = int(round(pos * inv_skew))
            buy_px = bb + 1 - max(0, skew)
            sell_px = ba - 1 - min(0, skew)
            buy_px = max(bb + 1, min(ba - 2, buy_px))
            sell_px = min(ba - 1, max(bb + 2, sell_px))

            buy_qty = mm_qty if mm_on else 0
            sell_qty = mm_qty if mm_on else 0

            if z is not None:
                if z < -z_in and pos < max_total:
                    buy_qty += qty_arb
                elif z > z_in and pos > -max_total:
                    sell_qty += qty_arb
                elif z_out > 0 and abs(z) < z_out:
                    if pos > 0: sell_qty += min(pos, max_total)
                    elif pos < 0: buy_qty += min(-pos, max_total)

            if pos >= max_total: buy_qty = 0
            if pos <= -max_total: sell_qty = 0

            buy_qty = max(0, min(buy_qty, cap_buy))
            sell_qty = max(0, min(sell_qty, cap_sell))

            orders: List[Order] = []
            if buy_qty > 0: orders.append(Order(sym, int(buy_px), buy_qty))
            if sell_qty > 0: orders.append(Order(sym, int(sell_px), -sell_qty))

            tb = sum(o.quantity for o in orders if o.quantity > 0)
            ts = sum(-o.quantity for o in orders if o.quantity < 0)
            if tb > cap_buy or ts > cap_sell:
                continue

            if orders:
                result[sym] = orders

        return result

_MEMBERS_ROBOT = [
    "ROBOT_DISHES",
    "ROBOT_IRONING",
    "ROBOT_LAUNDRY",
    "ROBOT_MOPPING",
    "ROBOT_VACUUMING",
]
_N_ROBOT = len(_MEMBERS_ROBOT)

class RobotStrategy(ClusterStrategy):
    """Trimmed-mean basket-residual MR + MM for ROBOT (DISHES excluded by LOO defensive)."""

    def _init_state(self) -> None:
        self.state_data = {
            "sd": [0.0] * _N_ROBOT,
            "sd2": [1.0] * _N_ROBOT,
            "ticks": 0,
            "pm": [0] * _N_ROBOT,
            "cm": 0.0,
            "hwm": 0.0,
            "fr": 0,
        }

    def load_state(self, saved: Dict[str, Any]) -> None:
        if not saved:
            self._init_state(); return
        try:
            self.state_data = {
                "sd": list(saved["sd"]),
                "sd2": list(saved["sd2"]),
                "ticks": int(saved["ticks"]),
                "pm": list(saved.get("pm", [0] * _N_ROBOT)),
                "cm": float(saved.get("cm", 0.0)),
                "hwm": float(saved.get("hwm", 0.0)),
                "fr": int(saved.get("fr", 0)),
            }
        except (KeyError, TypeError):
            self._init_state()

    def dump_state(self) -> Dict[str, Any]:
        if not self.state_data:
            self._init_state()
        s = self.state_data
        return {
            "sd": [round(x, 5) for x in s["sd"]],
            "sd2": [round(x, 5) for x in s["sd2"]],
            "ticks": s["ticks"],
            "pm": [int(x) for x in s["pm"]],
            "cm": round(s["cm"], 2),
            "hwm": round(s["hwm"], 2),
            "fr": s["fr"],
        }

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        if not self.state_data:
            self._init_state()
        p = self.params
        if not p:
            return {}
        alpha = p["alpha_slow"]
        z_in = p["z_in"]
        z_out = p["z_out"]
        qty_arb = p["qty_arb"]
        warmup = p["warmup"]
        mm_on = p["mm_on"]
        mm_qty = p["mm_qty"]
        inv_skew = p["inv_skew"]
        max_total = p["max_total_pos"]
        use_trim = p.get("use_trimmed_mean", True)
        dishes_off = p.get("dishes_disabled", True)
        cb_dd = p.get("cb_drawdown", 1500)
        cb_freeze = p.get("cb_freeze", 500)

        s = self.state_data
        sd = s["sd"]
        sd2 = s["sd2"]
        s["ticks"] += 1
        ticks = s["ticks"]

        pos_map = state.position if state.position else {}

        mids: List[Optional[float]] = []
        bbs: List[Optional[int]] = []
        bas: List[Optional[int]] = []

        for sym in _MEMBERS_ROBOT:
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                mids.append(None); bbs.append(None); bas.append(None)
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            mids.append((bb + ba) / 2.0)
            bbs.append(bb); bas.append(ba)

        basket_indices = list(range(_N_ROBOT))
        if dishes_off:
            basket_indices = [i for i in basket_indices if i != 0]

        valid_basket = [mids[i] for i in basket_indices if mids[i] is not None]
        if len(valid_basket) < 3:
            return {}

        if use_trim and len(valid_basket) >= 3:
            sv = sorted(valid_basket)
            basket_mean = sum(sv[1:-1]) / (len(sv) - 2)
        else:
            basket_mean = sum(valid_basket) / len(valid_basket)

        pm = s["pm"]
        mtm_delta = 0.0
        for i in range(_N_ROBOT):
            mid_i = mids[i]
            if mid_i is not None and pm[i] != 0:
                pos_i = pos_map.get(_MEMBERS_ROBOT[i], 0)
                mtm_delta += pos_i * (mid_i - pm[i])
            if mid_i is not None:
                pm[i] = int(mid_i)

        s["cm"] += mtm_delta
        s["hwm"] = max(s["hwm"], s["cm"])
        if s["cm"] < s["hwm"] - cb_dd:
            s["fr"] = ticks + cb_freeze
            s["hwm"] = s["cm"]
        frozen = ticks < s["fr"]

        zs: List[Optional[float]] = []
        for i in range(_N_ROBOT):
            m = mids[i]
            if m is None:
                zs.append(None); continue
            dev = m - basket_mean
            sd[i] = (1.0 - alpha) * sd[i] + alpha * dev
            sd2[i] = (1.0 - alpha) * sd2[i] + alpha * dev * dev
            var = max(1e-8, sd2[i] - sd[i] * sd[i])
            zs.append((dev - sd[i]) / math.sqrt(var))

        if ticks < warmup or frozen:
            return {}

        result: Dict[Symbol, List[Order]] = {}

        for i, sym in enumerate(_MEMBERS_ROBOT):
            if dishes_off and i == 0:
                continue
            if bbs[i] is None or bas[i] is None:
                continue
            bb = bbs[i]
            ba = bas[i]
            z = zs[i]
            pos = pos_map.get(sym, 0)
            limit = self.limits.get(sym, 10)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)

            skew = int(round(pos * inv_skew))
            buy_px = bb + 1 - max(0, skew)
            sell_px = ba - 1 - min(0, skew)
            buy_px = max(bb + 1, min(ba - 2, buy_px))
            sell_px = min(ba - 1, max(bb + 2, sell_px))

            buy_qty = mm_qty if mm_on else 0
            sell_qty = mm_qty if mm_on else 0

            if z is not None:
                if z < -z_in and pos < max_total:
                    buy_qty += qty_arb
                elif z > z_in and pos > -max_total:
                    sell_qty += qty_arb
                elif z_out > 0 and abs(z) < z_out:
                    if pos > 0: sell_qty += min(pos, max_total)
                    elif pos < 0: buy_qty += min(-pos, max_total)

            if pos >= max_total: buy_qty = 0
            if pos <= -max_total: sell_qty = 0

            buy_qty = max(0, min(buy_qty, cap_buy))
            sell_qty = max(0, min(sell_qty, cap_sell))

            orders: List[Order] = []
            if buy_qty > 0: orders.append(Order(sym, int(buy_px), buy_qty))
            if sell_qty > 0: orders.append(Order(sym, int(sell_px), -sell_qty))

            tb = sum(o.quantity for o in orders if o.quantity > 0)
            ts = sum(-o.quantity for o in orders if o.quantity < 0)
            if tb > cap_buy or ts > cap_sell:
                continue

            if orders:
                result[sym] = orders

        return result

_MEMBERS_GALAXY_SOUNDS = [
    "GALAXY_SOUNDS_BLACK_HOLES",
    "GALAXY_SOUNDS_DARK_MATTER",
    "GALAXY_SOUNDS_PLANETARY_RINGS",
    "GALAXY_SOUNDS_SOLAR_FLAMES",
    "GALAXY_SOUNDS_SOLAR_WINDS",
]
_N_GALAXY_SOUNDS = len(_MEMBERS_GALAXY_SOUNDS)

class GalaxySoundsStrategy(ClusterStrategy):
    """Trimmed-mean basket-residual MR + MM with hard 100-tick CB."""

    def _init_state(self) -> None:
        self.state_data = {
            "sd": [0.0] * _N_GALAXY_SOUNDS,
            "sd2": [1.0] * _N_GALAXY_SOUNDS,
            "ticks": 0,
            "pm": [0] * _N_GALAXY_SOUNDS,
            "cm": 0.0,
            "hwm": 0.0,
            "fr": 0,
            "wm": 0.0,
            "wt": 0,
        }

    def load_state(self, saved: Dict[str, Any]) -> None:
        if not saved:
            self._init_state(); return
        try:
            self.state_data = {
                "sd": list(saved["sd"]),
                "sd2": list(saved["sd2"]),
                "ticks": int(saved["ticks"]),
                "pm": list(saved.get("pm", [0] * _N_GALAXY_SOUNDS)),
                "cm": float(saved.get("cm", 0.0)),
                "hwm": float(saved.get("hwm", 0.0)),
                "fr": int(saved.get("fr", 0)),
                "wm": float(saved.get("wm", 0.0)),
                "wt": int(saved.get("wt", 0)),
            }
        except (KeyError, TypeError):
            self._init_state()

    def dump_state(self) -> Dict[str, Any]:
        if not self.state_data:
            self._init_state()
        s = self.state_data
        return {
            "sd": [round(x, 5) for x in s["sd"]],
            "sd2": [round(x, 5) for x in s["sd2"]],
            "ticks": s["ticks"],
            "pm": [int(x) for x in s["pm"]],
            "cm": round(s["cm"], 2),
            "hwm": round(s["hwm"], 2),
            "fr": s["fr"],
            "wm": round(s["wm"], 2),
            "wt": s["wt"],
        }

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        if not self.state_data:
            self._init_state()
        p = self.params
        if not p:
            return {}
        alpha = p["alpha_slow"]
        z_in = p["z_in"]
        z_out = p["z_out"]
        qty_arb = p["qty_arb"]
        warmup = p["warmup"]
        mm_on = p["mm_on"]
        mm_qty = p["mm_qty"]
        inv_skew = p["inv_skew"]
        max_total = p["max_total_pos"]
        use_trim = p.get("use_trimmed_mean", True)
        cb_win_dd = p.get("cb_window_dd", 1500)
        cb_win_tks = p.get("cb_window_ticks", 100)
        cb_freeze = p.get("cb_freeze", 500)
        cb_dd = p.get("cb_drawdown", 3000)

        s = self.state_data
        sd = s["sd"]
        sd2 = s["sd2"]
        s["ticks"] += 1
        ticks = s["ticks"]

        pos_map = state.position if state.position else {}

        mids: List[Optional[float]] = []
        bbs: List[Optional[int]] = []
        bas: List[Optional[int]] = []

        for sym in _MEMBERS_GALAXY_SOUNDS:
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                mids.append(None); bbs.append(None); bas.append(None)
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            mids.append((bb + ba) / 2.0)
            bbs.append(bb); bas.append(ba)

        valid = [m for m in mids if m is not None]
        if len(valid) < 3:
            return {}

        if use_trim and len(valid) >= 3:
            sv = sorted(valid)
            basket_mean = sum(sv[1:-1]) / (len(sv) - 2)
        else:
            basket_mean = sum(valid) / len(valid)

        pm = s["pm"]
        mtm_delta = 0.0
        for i in range(_N_GALAXY_SOUNDS):
            mid_i = mids[i]
            if mid_i is not None and pm[i] != 0:
                pos_i = pos_map.get(_MEMBERS_GALAXY_SOUNDS[i], 0)
                mtm_delta += pos_i * (mid_i - pm[i])
            if mid_i is not None:
                pm[i] = int(mid_i)

        s["cm"] += mtm_delta
        s["hwm"] = max(s["hwm"], s["cm"])
        if s["cm"] < s["hwm"] - cb_dd:
            s["fr"] = ticks + cb_freeze
            s["hwm"] = s["cm"]

        if ticks - s["wt"] >= cb_win_tks:
            window_pnl = s["cm"] - s["wm"]
            if window_pnl < -cb_win_dd:
                s["fr"] = max(s["fr"], ticks + cb_freeze)
            s["wm"] = s["cm"]
            s["wt"] = ticks

        frozen = ticks < s["fr"]

        zs: List[Optional[float]] = []
        for i in range(_N_GALAXY_SOUNDS):
            m = mids[i]
            if m is None:
                zs.append(None); continue
            dev = m - basket_mean
            sd[i] = (1.0 - alpha) * sd[i] + alpha * dev
            sd2[i] = (1.0 - alpha) * sd2[i] + alpha * dev * dev
            var = max(1e-8, sd2[i] - sd[i] * sd[i])
            zs.append((dev - sd[i]) / math.sqrt(var))

        if ticks < warmup or frozen:
            return {}

        result: Dict[Symbol, List[Order]] = {}

        for i, sym in enumerate(_MEMBERS_GALAXY_SOUNDS):
            if bbs[i] is None or bas[i] is None:
                continue
            bb = bbs[i]
            ba = bas[i]
            z = zs[i]
            pos = pos_map.get(sym, 0)
            limit = self.limits.get(sym, 10)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)

            skew = int(round(pos * inv_skew))
            buy_px = bb + 1 - max(0, skew)
            sell_px = ba - 1 - min(0, skew)
            buy_px = max(bb + 1, min(ba - 2, buy_px))
            sell_px = min(ba - 1, max(bb + 2, sell_px))

            buy_qty = mm_qty if mm_on else 0
            sell_qty = mm_qty if mm_on else 0

            if z is not None:
                if z < -z_in and pos < max_total:
                    buy_qty += qty_arb
                elif z > z_in and pos > -max_total:
                    sell_qty += qty_arb
                elif z_out > 0 and abs(z) < z_out:
                    if pos > 0: sell_qty += min(pos, max_total)
                    elif pos < 0: buy_qty += min(-pos, max_total)

            if pos >= max_total: buy_qty = 0
            if pos <= -max_total: sell_qty = 0

            buy_qty = max(0, min(buy_qty, cap_buy))
            sell_qty = max(0, min(sell_qty, cap_sell))

            orders: List[Order] = []
            if buy_qty > 0: orders.append(Order(sym, int(buy_px), buy_qty))
            if sell_qty > 0: orders.append(Order(sym, int(sell_px), -sell_qty))

            tb = sum(o.quantity for o in orders if o.quantity > 0)
            ts = sum(-o.quantity for o in orders if o.quantity < 0)
            if tb > cap_buy or ts > cap_sell:
                continue

            if orders:
                result[sym] = orders

        return result

_MEMBERS_SLEEP_POD = [
    "SLEEP_POD_COTTON",
    "SLEEP_POD_LAMB_WOOL",
    "SLEEP_POD_NYLON",
    "SLEEP_POD_POLYESTER",
    "SLEEP_POD_SUEDE",
]
_N_SLEEP_POD = len(_MEMBERS_SLEEP_POD)

class SleepPodStrategy(ClusterStrategy):
    """Trimmed-mean basket-residual MR + MM with σ-explosion guard + rolling CB."""

    def _init_state(self) -> None:
        self.state_data = {
            "sd": [0.0] * _N_SLEEP_POD,
            "sd2": [1.0] * _N_SLEEP_POD,
            "ticks": 0,
            "pm": [0] * _N_SLEEP_POD,
            "cm": 0.0,
            "hwm": 0.0,
            "fr": 0,
            "bf": 0.0,
            "bs": 0.0,
            "wm": 0.0,
            "wt": 0,
        }

    def load_state(self, saved: Dict[str, Any]) -> None:
        if not saved:
            self._init_state(); return
        try:
            self.state_data = {
                "sd": list(saved["sd"]),
                "sd2": list(saved["sd2"]),
                "ticks": int(saved["ticks"]),
                "pm": list(saved.get("pm", [0] * _N_SLEEP_POD)),
                "cm": float(saved.get("cm", 0.0)),
                "hwm": float(saved.get("hwm", 0.0)),
                "fr": int(saved.get("fr", 0)),
                "bf": float(saved.get("bf", 0.0)),
                "bs": float(saved.get("bs", 0.0)),
                "wm": float(saved.get("wm", 0.0)),
                "wt": int(saved.get("wt", 0)),
            }
        except (KeyError, TypeError):
            self._init_state()

    def dump_state(self) -> Dict[str, Any]:
        if not self.state_data:
            self._init_state()
        s = self.state_data
        return {
            "sd": [round(x, 5) for x in s["sd"]],
            "sd2": [round(x, 5) for x in s["sd2"]],
            "ticks": s["ticks"],
            "pm": [int(x) for x in s["pm"]],
            "cm": round(s["cm"], 2),
            "hwm": round(s["hwm"], 2),
            "fr": s["fr"],
            "bf": round(s["bf"], 4),
            "bs": round(s["bs"], 4),
            "wm": round(s["wm"], 2),
            "wt": s["wt"],
        }

    def update(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        if not self.state_data:
            self._init_state()
        p = self.params
        if not p:
            return {}
        alpha = p["alpha_slow"]
        alpha_fast = p.get("alpha_fast", 0.02)
        vol_mul = p.get("vol_mul", 1.8)
        z_in = p["z_in"]
        z_out = p["z_out"]
        qty_arb = p["qty_arb"]
        warmup = p["warmup"]
        mm_on = p["mm_on"]
        mm_qty = p["mm_qty"]
        inv_skew = p["inv_skew"]
        max_total = p["max_total_pos"]
        use_trim = p.get("use_trimmed_mean", True)
        cb_dd = p.get("cb_drawdown", 2000)
        cb_freeze = p.get("cb_freeze", 500)
        cb_win_dd = p.get("cb_window_dd", 2000)
        cb_win_tks = p.get("cb_window_ticks", 200)

        s = self.state_data
        sd = s["sd"]
        sd2 = s["sd2"]
        s["ticks"] += 1
        ticks = s["ticks"]

        pos_map = state.position if state.position else {}

        mids: List[Optional[float]] = []
        bbs: List[Optional[int]] = []
        bas: List[Optional[int]] = []

        for sym in _MEMBERS_SLEEP_POD:
            od = state.order_depths.get(sym)
            if od is None or not od.buy_orders or not od.sell_orders:
                mids.append(None); bbs.append(None); bas.append(None)
                continue
            bb = max(od.buy_orders)
            ba = min(od.sell_orders)
            mids.append((bb + ba) / 2.0)
            bbs.append(bb); bas.append(ba)

        valid = [m for m in mids if m is not None]
        if len(valid) < 3:
            return {}

        if use_trim and len(valid) >= 3:
            sv = sorted(valid)
            basket_mean = sum(sv[1:-1]) / (len(sv) - 2)
        else:
            basket_mean = sum(valid) / len(valid)

        basket_residual = abs(sum(valid) / len(valid) - basket_mean)
        s["bf"] = (1 - alpha_fast) * s["bf"] + alpha_fast * basket_residual
        s["bs"] = (1 - alpha) * s["bs"] + alpha * basket_residual
        vol_stressed = (s["bs"] > 0.5) and (s["bf"] > vol_mul * s["bs"])
        size_scale = 0.5 if vol_stressed else 1.0

        pm = s["pm"]
        mtm_delta = 0.0
        for i in range(_N_SLEEP_POD):
            mid_i = mids[i]
            if mid_i is not None and pm[i] != 0:
                pos_i = pos_map.get(_MEMBERS_SLEEP_POD[i], 0)
                mtm_delta += pos_i * (mid_i - pm[i])
            if mid_i is not None:
                pm[i] = int(mid_i)

        s["cm"] += mtm_delta
        s["hwm"] = max(s["hwm"], s["cm"])
        if s["cm"] < s["hwm"] - cb_dd:
            s["fr"] = max(s["fr"], ticks + cb_freeze)
            s["hwm"] = s["cm"]

        if ticks - s["wt"] >= cb_win_tks:
            window_pnl = s["cm"] - s["wm"]
            if window_pnl < -cb_win_dd:
                s["fr"] = max(s["fr"], ticks + cb_freeze)
            s["wm"] = s["cm"]
            s["wt"] = ticks

        frozen = ticks < s["fr"]

        zs: List[Optional[float]] = []
        for i in range(_N_SLEEP_POD):
            m = mids[i]
            if m is None:
                zs.append(None); continue
            dev = m - basket_mean
            sd[i] = (1.0 - alpha) * sd[i] + alpha * dev
            sd2[i] = (1.0 - alpha) * sd2[i] + alpha * dev * dev
            var = max(1e-8, sd2[i] - sd[i] * sd[i])
            zs.append((dev - sd[i]) / math.sqrt(var))

        if ticks < warmup or frozen:
            return {}

        result: Dict[Symbol, List[Order]] = {}

        for i, sym in enumerate(_MEMBERS_SLEEP_POD):
            if bbs[i] is None or bas[i] is None:
                continue
            bb = bbs[i]
            ba = bas[i]
            z = zs[i]
            pos = pos_map.get(sym, 0)
            limit = self.limits.get(sym, 10)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)

            skew = int(round(pos * inv_skew))
            buy_px = bb + 1 - max(0, skew)
            sell_px = ba - 1 - min(0, skew)
            buy_px = max(bb + 1, min(ba - 2, buy_px))
            sell_px = min(ba - 1, max(bb + 2, sell_px))

            eff_mm_qty = max(1, int(mm_qty * size_scale)) if mm_on else 0

            buy_qty = eff_mm_qty
            sell_qty = eff_mm_qty

            if z is not None:
                eff_arb = max(0, int(qty_arb * size_scale))
                if z < -z_in and pos < max_total:
                    buy_qty += eff_arb
                elif z > z_in and pos > -max_total:
                    sell_qty += eff_arb
                elif z_out > 0 and abs(z) < z_out:
                    if pos > 0: sell_qty += min(pos, max_total)
                    elif pos < 0: buy_qty += min(-pos, max_total)

            if pos >= max_total: buy_qty = 0
            if pos <= -max_total: sell_qty = 0

            buy_qty = max(0, min(buy_qty, cap_buy))
            sell_qty = max(0, min(sell_qty, cap_sell))

            orders: List[Order] = []
            if buy_qty > 0: orders.append(Order(sym, int(buy_px), buy_qty))
            if sell_qty > 0: orders.append(Order(sym, int(sell_px), -sell_qty))

            tb = sum(o.quantity for o in orders if o.quantity > 0)
            ts = sum(-o.quantity for o in orders if o.quantity < 0)
            if tb > cap_buy or ts > cap_sell:
                continue

            if orders:
                result[sym] = orders

        return result

GLOBAL_DRAWDOWN_HALT: int = -20_000

CLUSTER_TICK_VOL_CAP: int = 200

HALT_FLATTEN_TICKS: int = 100

class Trader:
    HYBRID_VARIANT: str = "H5"

    _A_PARAMS_OVERRIDE: Dict[str, Dict[str, Any]] = {
        "UV_VISOR":     PARAMS_A_UV_VISOR,
        "TRANSLATOR":   PARAMS_A_TRANSLATOR,
        "SLEEP_POD":    PARAMS_A_SLEEP_POD,
        "OXYGEN_SHAKE": PARAMS_A_OXYGEN_SHAKE,
    }
    _A_CLUSTERS_BY_VARIANT: Dict[str, set] = {
        "B":     set(),
        "H1":    {"UV_VISOR"},
        "H2":    {"UV_VISOR", "TRANSLATOR"},
        "H3":    {"UV_VISOR", "TRANSLATOR", "SLEEP_POD"},
        "H4":    {"UV_VISOR", "TRANSLATOR", "SLEEP_POD", "OXYGEN_SHAKE"},
        "H5":    {"UV_VISOR", "TRANSLATOR", "OXYGEN_SHAKE"},
    }

    _STRATEGY_CLS: Dict[str, type] = {
        "PEBBLES": PebblesBasketArb,
        "SNACKPACK": SnackpackPairMR,
        "MICROCHIP": MicrochipPCAResid,
        "OXYGEN_SHAKE": OxygenShakeStrategy,
        "PANEL": PanelStrategy,
        "UV_VISOR": UVVisorStrategy,
        "TRANSLATOR": TranslatorStrategy,
        "GALAXY_SOUNDS": GalaxySoundsStrategy,
        "ROBOT": RobotStrategy,
        "SLEEP_POD": SleepPodStrategy,
    }

    def __init__(self) -> None:
        self._strategies: Dict[str, ClusterStrategy] = {}
        self._a_style_products: set = set()
        a_clusters = self._A_CLUSTERS_BY_VARIANT.get(self.HYBRID_VARIANT, set())
        for name, members in CLUSTERS.items():
            if name in a_clusters:
                cls: type = AStyleMMStrategy
                params = self._A_PARAMS_OVERRIDE[name]
                self._a_style_products.update(members)
            else:
                params = _CLUSTER_PARAMS[name]
                cls = self._STRATEGY_CLS.get(name, SkeletonClusterStrategy)
            self._strategies[name] = cls(
                cluster_name=name,
                members=members,
                params=params,
                limits=LIMITS,
            )

    _SCHEMA_VERSION = 1

    def _load_trader_data(self, raw: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Return (clusters_state, global_state)."""
        if not raw:
            return {}, {}
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get("v") != self._SCHEMA_VERSION:
                return {}, {}
            return data.get("clusters", {}), data.get("global", {})
        except Exception:
            return {}, {}

    def _dump_trader_data(
        self,
        clusters_state: Dict[str, Any],
        global_state: Dict[str, Any],
    ) -> str:
        return json.dumps(
            {"v": self._SCHEMA_VERSION, "clusters": clusters_state, "global": global_state},
            separators=(",", ":"),
        )

    @staticmethod
    def _clip_orders(
        result: Dict[str, List[Order]],
        position: Dict[str, int],
        bypass: Optional[set] = None,
    ) -> Dict[str, List[Order]]:
        """
        For each product, verify aggregate buy and sell quantities do not
        exceed the available position headroom.  If a breach is detected,
        drop ALL orders for that product (matching backtester semantics).

        Products in `bypass` are passed through unchanged — used for
        AStyleMMStrategy clusters whose `lim - position` headroom formula
        matches the actual backtester's check (more permissive than this
        guard's `lim - max(0, pos)` rule).
        """
        bypass = bypass or set()
        clipped: Dict[str, List[Order]] = {}
        for symbol, orders in result.items():
            if symbol in bypass:
                clipped[symbol] = orders
                continue
            if not orders:
                clipped[symbol] = orders
                continue
            limit = LIMITS.get(symbol, 0)
            pos = position.get(symbol, 0)
            cap_buy = limit - max(0, pos)
            cap_sell = limit - max(0, -pos)
            total_buy = sum(o.quantity for o in orders if o.quantity > 0)
            total_sell = sum(-o.quantity for o in orders if o.quantity < 0)
            if total_buy > cap_buy or total_sell > cap_sell:

                logger.print(
                    f"[CLIP] {symbol}: buy={total_buy}/{cap_buy}"
                    f" sell={total_sell}/{cap_sell} -- orders dropped"
                )
                clipped[symbol] = []
            else:
                clipped[symbol] = orders
        return clipped

    def run(
        self, state: TradingState
    ) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}
        clusters_state: Dict[str, Any] = {}
        position: Dict[str, int] = state.position if state.position else {}

        saved_clusters, _ = self._load_trader_data(state.traderData)

        for name, strategy in self._strategies.items():
            try:
                strategy.load_state(saved_clusters.get(name, {}))
            except Exception as e:
                logger.print(f"[STATE_LOAD ERR] {name}: {e}")

        for name, strategy in self._strategies.items():
            try:
                cluster_orders = strategy.update(state)

                tick_vol = sum(
                    abs(o.quantity)
                    for orders in cluster_orders.values()
                    for o in orders
                )
                if tick_vol > CLUSTER_TICK_VOL_CAP:
                    logger.print(
                        f"[VOL_CAP] {name}: tick_vol={tick_vol} > {CLUSTER_TICK_VOL_CAP}"
                        " — cluster orders zeroed"
                    )
                    cluster_orders = {}

                for symbol, orders in cluster_orders.items():
                    if symbol in result:
                        result[symbol] = result[symbol] + orders
                    else:
                        result[symbol] = orders
            except Exception as e:
                logger.print(f"[CLUSTER ERR] {name}: {e}")

        result = self._clip_orders(result, position, bypass=self._a_style_products)

        for name, strategy in self._strategies.items():
            try:
                clusters_state[name] = strategy.dump_state()
            except Exception as e:
                logger.print(f"[STATE_DUMP ERR] {name}: {e}")

        trader_data = self._dump_trader_data(clusters_state, {})
        conversions = 0
        logger.flush(state, result, conversions, trader_data)
        return (result, conversions, trader_data)