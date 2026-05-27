# Round 4 · Algorithmic

| | |
|---|---|
| Final live PnL | **+25,351** XIRECs |
| Algorithmic rank | 1,149 |
| Submitted file | [`trader.py`](trader.py) (97 KB, stdlib only) |
| Historical data used | `data/prices_round_4_day_{1,2,3}.csv` + matching trades |

## Products

Identical to Round 3 — `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`, `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, and the ten `VEV_K` vouchers — but the vouchers have shorter time-to-expiry. Same code, decremented `TTE_DAYS_LIVE`.

## What changed from Round 3

The Round 4 file is the R3 file with sweep-confirmed parameter changes:

- `V09A_EOD_WINDOW = 9200` (sweep winner over {8500, 9000, 9200, 9500, 10000}) — the end-of-day flatten window for HP.
- `V09A_EDGE_MULT_5100 = 0.25` (sweep winner) — tighter edge for the K = 5100 voucher; the previous floor of 1.0 was wider than the vega edge of ~0.775 and hurt fills.
- VEV_5300 outlier detector latch policy tightened so that on a latched day, passive smile MM is also zeroed out for that strike (not just the MR overlay).
- Deep-OTM voucher absolute-edge override generalised — when `voucher_mid < 10`, edge defaults to 1.

No new classes, no new techniques. All R3 citations carry forward identically.

## Papers and references

Inherited unchanged from Round 3:

- Black & Scholes (1973), Avellaneda & Stoikov (2008), Stoikov micro-price (2018), Huang–Lehalle–Rosenbaum (2015), jmerle voucher template, Frankfurt StaticTrader, Gatheral parabolic SVI, Spokoiny LPA.

Papers surveyed during R4 and **not** shipped (the full list with rejection reasons is in [`../../docs/literature_review.md`](../../docs/literature_review.md)):

- Glosten & Milgrom (1985) PIN — counterparty classification not integrated into shipped code.
- Easley, López de Prado & O'Hara (2011) VPIN — we shipped a simpler fill-direction tracking gate instead.
- Cartea & Jaimungal (2015) "Algorithmic Trading with Model Uncertainty" — dynamic spread per counterparty not integrated.
- Hull & White (1987) stochastic volatility / gamma scalping — no discrete-rebalance gamma scalping.
- Christoffersen & Jacobs (2004) Kalman IV filter — OLS + EMA used instead.
- Cont & Kukanov (2013) optimal liquidation — no VWAP schedule.

## Reproducing the backtest

```bash
prosperity4btest cli round_4/algorithmic/trader.py 3
```
