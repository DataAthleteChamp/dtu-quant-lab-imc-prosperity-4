# Round 4 — DTU Quant Lab

| Metric | Value |
|---|---|
| Algorithmic PnL | **+25,351** (rank 1,149) |
| Manual PnL | **+23,566** (rank 699) |
| Round total | 48,917 |
| Cumulative (finals) | 130,828 |
| Global position end of round | 1,372 |

A modest recovery round. The algorithmic leg returned to positive territory after the R3 collapse and the manual gave us a smaller-than-usual contribution. The position climbed from #1,742 to #1,372 — still nowhere near the leaderboard, but stable enough to set up the R5 push.

## What was traded

No new products. The Round 4 algorithmic trader is the Round 3 file with `TTE_DAYS_LIVE` decremented (vouchers have one less day to expiry) and tightened parameters on the voucher edge and HP regime detector. The manual round was an options chain.

See [`algorithmic/`](algorithmic/) and [`manual/`](manual/).

## Result screenshot

![Round 4 detailed results](../docs/results/round_4.png)

Algorithmic PnL curve from the live submission — flat-with-drift, characteristic of a parameter sweep on an already-shaped strategy:

![Round 4 algorithmic PnL](../docs/results/algo_round_4.png)

## What we learned

- After spending Round 3 reading literature on PIN (Glosten–Milgrom), VPIN (Easley–López de Prado–O'Hara), Cartea–Jaimungal dynamic spread, Hull–White stochastic volatility, Cont–Kukanov liquidation, and per-counterparty profiling, almost none of it shipped. The R4 edits were a small set of parameter sweeps over the existing R3 trader.
- The honest takeaway is that **paper-driven iteration scales sublinearly** once a strategy has a coherent shape. The remaining edge in the R4 voucher chain was buried in numerical parameters that needed sweeping, not in a new theoretical framework.
- This is the lesson that shaped Round 5: we abandoned single-product theoretical iteration and switched to a cluster-strategy architecture that let multiple shipped variants coexist.

## Analysis on shipped data

<p align="center">
  <img src="../docs/plots/round_4/hydrogel_regime.png" alt="Hydrogel regime detector overlay" width="100%">
</p>

A rolling-500 median anchor with a ±1.5σ band classifies 23% of ticks as PINNED, 29% as TRENDING and 47% as NOISY on day 2. The trader runs three sub-strategies in parallel, one per regime, with inventory skew flipping sign when |z| crosses the TRENDING threshold.

<p align="center">
  <img src="../docs/plots/round_4/voucher_market_vs_fair.png" alt="Voucher market vs Black-Scholes fair" width="100%">
</p>

A flat-σ = 0.20 Black–Scholes anchor systematically over- and under-prices the chain symmetrically — that is the R3 mistake. R4's parabolic smile correction trims the high-OTM and low-OTM mispricing and recovered enough edge to lift algo rank from 2,232 to 1,149.

## In hindsight

We should have shipped the parabolic IV correction in Round 3, not Round 4 — the smile shape is visible on day-0 data and the fix is a single quadratic regression. The fact that we instead spent Round 3 reading microstructure papers and Round 4 catching up with the obvious fix is exactly the failure mode the Round 5 cluster architecture was designed to prevent: when one strategy is broken, the iteration budget should flow to triage, not to theory.
