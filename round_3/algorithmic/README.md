# Round 3 · Algorithmic

| | |
|---|---|
| Final live PnL | **+3,686** XIRECs |
| Algorithmic rank | 2,232 |
| Submitted file | [`trader.py`](trader.py) (87 KB, stdlib only) |
| Historical data used | `data/prices_round_3_day_{0,1,2}.csv` + matching trades |

## Products

| Symbol | Position limit | Microstructure |
|---|---|---|
| `ASH_COATED_OSMIUM` | 50 | Pegged ~10,000 (R2 logic verbatim) |
| `INTARIAN_PEPPER_ROOT` | 50 | Drift (R2 logic verbatim) |
| `HYDROGEL_PACK` (HP) | 50 | Stationary spot — *but* prone to multi-tick drifts |
| `VELVETFRUIT_EXTRACT` (VEV) | 200 | Mean-reverting underlying for the voucher chain |
| `VEV_K` for K ∈ {4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500} | 200 each | European call vouchers — Black–Scholes priced |

## Final strategy

### HYDROGEL_PACK — 3-state regime detector
A PINNED state market-makes around a rolling-median anchor; a NOISY state widens spreads; a TRENDING state (triggered when `|EMA_short(50) − EMA_long(500)| > k · σ`) caps the position at 50 with edge = 6 and biases the inventory **with** the drift. This regime separation was added in v07 after a v06 bug allowed the static FV trader to keep buying through a 70-tick HP drawdown on a live day.

### VELVETFRUIT_EXTRACT — mean-reversion + spot hedge

A rolling z-score on the VEV mid drives a mean-reversion overlay (`z ≥ 2.0` to enter, `z ≤ 0.0` to exit) combined with an inside-spread MM.

### VEV vouchers — Black–Scholes with parabolic smile

The voucher chain is priced from a flat global IV (σ = 0.25) refined by a per-tick parabolic IV smile fit:

```
σ(m) = c + b · m + a · m²            where m = log(K/S) / √T
```

Coefficients `(a, b, c)` are smoothed by exponential moving average. For each strike at each tick the trader computes fair = `BS_CALL(S, K, T, 0, σ_K)`, an edge `e = max(0.1, vega · iv_uncertainty)`, and quotes / takes accordingly. Deep-OTM vouchers (`mid < 10`) use an absolute edge override.

A V09a outlier detector latches on `VEV_5300` when its residual to the smile fit exceeds a daily threshold and zeros out passive MM for that strike for the remainder of the day.

### Delta-hedge overlay

```
D = Σ_K δ_K · pos_K
if |D| > HEDGE_TRIGGER: offset via VEV_EXTRACT spot orders
```

The delta-hedge unwinds aggregate exposure rather than per-strike exposure, mirroring the jmerle Prosperity 2 9th-place voucher template's structure.

## Papers and references used (shipped in the code)

| Citation | Where it lives in `trader.py` |
|---|---|
| Black & Scholes (1973) | `bs_call()`, `bs_call_vega()`, `implied_vol()` |
| Avellaneda & Stoikov (2008) | `_trade_hp_as_mm()` inventory skew |
| Stoikov (2018) micro-price (SSRN 2970694) | `get_micro_price()` |
| Huang, Lehalle & Rosenbaum (2015) Queue-Reactive Model | QI-scaled quoting |
| jmerle — IMC Prosperity 2 9th-place voucher template | `trade_voucher()` swing logic — explicit credit in the module docstring |
| Frankfurt Hedgehogs StaticTrader (TimoDiehm/imc-prosperity-3) | `_trade_hp_static()` |
| Gatheral — SVI parametrisation (parabolic variant) | `_fit_smile()` — quadratic in log-moneyness |
| EMA 3-state regime detector | PARAMS_HP_REGIME |
| Spokoiny LPA | safe-mode guard (inherited from R1/R2) |

## Papers surveyed but not shipped

Cartea & Jaimungal Ch. 10 (per-fill adverse-selection penalty), Sinclair *Volatility Trading* gamma scalping (no continuous hedge underlier was available), Vidyamurthy *Pairs Trading* deep-ITM 4000/4500 pairs (thin books), Roll (1984) bid-ask bounce gate. Inventory in [`../../docs/literature_review.md`](../../docs/literature_review.md).

## Reproducing the backtest

```bash
prosperity4btest cli round_3/algorithmic/trader.py 2
```
