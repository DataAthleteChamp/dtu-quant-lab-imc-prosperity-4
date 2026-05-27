# Round 1 · Algorithmic

| | |
|---|---|
| Final live PnL | **+67,585** XIRECs |
| Algorithmic rank | 3,646 |
| Submitted file | [`trader.py`](trader.py) (19 KB, stdlib only) |
| Historical data used | `data/prices_round_1_day_{-2,-1,0}.csv` + matching trades |

## Products

| Symbol | Position limit | Microstructure |
|---|---|---|
| `ASH_COATED_OSMIUM` | 50 | Pegged ~10,000, mean-reverting (Hurst 0.39, VR(100) = 0.03, half-life ≈ 8.4 ticks) |
| `INTARIAN_PEPPER_ROOT` | 50 | Slow linear trend, drift ≈ +0.001 per timestamp |

## Final strategy

### OSMIUM — pegged market making
A fixed fair value of 10,000 anchors the quoting loop. Each tick:
1. **Take** any visible bid above or ask below the fair value, sized by remaining capacity.
2. **Penny-jump** the inside book on both sides when our position is small.
3. **Two-level posting** with a 60 / 40 split of the remaining capacity (Guéant–Lehalle 2012), and a Stoikov micro-price refinement of the fair-value anchor when the order-book imbalance signal is strong (correlation OBI vs next-tick mid = +0.38 on historical data).
4. **Graduated urgent flatten** at `|pos| >= 30` (−2 tick price improvement) and `|pos| >= 38` (−5 tick) — opportunity-cost argument derived from A-S inventory theory. This was the largest single PnL improvement we found.
5. A Spokoiny-LPA-inspired safe-mode guard rail trips the trader into flatten-only when one-sided book pressure exceeds a calibrated threshold.

### PEPPER ROOT — trend-carry plus market making
1. Fair value modelled as `start_price + 0.001 · timestamp`.
2. Asymmetric inventory skew: long positions are cheap to hold (the drift works for you), short positions are expensive.
3. Maintain a long bias so the carry compounds.

## Papers and references used (shipped in the code)

| Citation | Where it lives in `trader.py` |
|---|---|
| Avellaneda & Stoikov (2008), "High-Frequency Trading in a Limit Order Book" | Module docstring; inventory skew |
| Guéant & Lehalle (2012), "Dealing with the Inventory Risk" | 60 / 40 two-level posting |
| Stoikov (2018), "The Micro-Price" (SSRN 2970694) | `get_micro_price()` |
| Huang, Lehalle & Rosenbaum (2015), "Queue-Reactive Model" | QI-based quote scaling |
| Spokoiny — Local Polynomial Adaptation (LPA) | Safe-mode guard rail |
| Lo & MacKinlay (1988), variance ratio test | Module docstring (statistic only) |
| Frankfurt Hedgehogs (TimoDiehm/imc-prosperity-3) — Rainforest Resin pattern | OSMIUM TAKE / FLATTEN / PENNY-JUMP skeleton |

A larger inventory of papers we tested **and rejected** — Ho & Stoll (1981), full Stoikov micro-price as FV, OBI-asymmetric quoting (Cartea–Jaimungal), Krugman target-zone peg defence, VPIN (Easley–López de Prado–O'Hara), Hawkes self-exciting processes (Bacry–Mastromatteo–Muzy), Cont trade-sign imbalance, and a survey of Chinese HFT literature — is in [`../../docs/literature_review.md`](../../docs/literature_review.md) with the backtest number that killed each one.

## Reproducing the backtest

```bash
pip install prosperity4btest==5.0.0
prosperity4btest cli round_1/algorithmic/trader.py 0
```

The day-0 backtest is the most representative single-day check; days −1 and −2 are also included in `data/` and can be appended.
