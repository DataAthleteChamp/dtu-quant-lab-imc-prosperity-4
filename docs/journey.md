# The campaign — DTU Quant Lab in IMC Prosperity 4

This is the long-form story of how a first-time team finished 28th worldwide out of 18,803 in IMC Prosperity 4.

## The qualifier

The qualifier comprises Rounds 1 and 2 and admits the top 2,000 teams to the finals. We placed:

- **Round 1**: algorithmic +67,585 (rank 3,646), manual +85,000 (**25th**), cumulative 152,585, global #2,609.
- **Round 2**: algorithmic +84,889 (rank 1,999), manual +204,456 (**58th**), cumulative **441,929**, global #1,123.

Cumulative 441,929 XIRECs cleared the qualifier threshold comfortably. Augusto Villoldo's two top-100 manual finishes carried the team — the algorithmic leg averaged near the field median.

## The Round 3 collapse

The finals reset cumulative PnL to zero. Round 3 introduced ten European call vouchers on a new mean-reverting underlying, a third stationary spot product (HYDROGEL_PACK), and a Black–Scholes voucher chain to market-make. Our R3 trader shipped with a static market-maker on HP that worked beautifully on the OSMIUM peg from rounds 1 and 2 but broke catastrophically when HP drifted 70 ticks over a single session — the fixed-FV anchor kept buying into the drawdown. The voucher chain shipped with too-conservative IV anchoring and missed most of the available edge.

The Round 3 algorithmic result was **+3,686** — rank 2,232, very close to flat. Augusto's third consecutive top-100 manual finish (**69th**, +78,225) was the only reason the round closed materially positive at all.

End of Round 3: **global position #1,742**. The low point of the campaign.

## The Round 4 stabilisation

We diagnosed the R3 HP trader bug and shipped a three-state regime detector (PINNED / TRENDING / NOISY) with a rolling-median anchor and inventory skew leaning *with* the drift. Voucher edges were tightened via parameter sweeps (`V09A_EDGE_MULT_5100 = 0.25`, `V09A_EOD_WINDOW = 9200`). A `VEV_5300` outlier detector latched off passive market-making on that strike on outlier days. We surveyed Glosten–Milgrom PIN, VPIN, Cartea–Jaimungal dynamic spread, Hull–White stochastic vol, Cont–Kukanov liquidation — almost none of which made it into the live code.

The Round 4 algorithmic result was **+25,351** (rank 1,149), the manual a smaller **+23,566** (rank 699). Cumulative recovered to 130,828, global position climbed to #1,372. Still far from contention, but the floor was holding.

## The Round 5 comeback

The strategic decision before Round 5 was to **abandon monolithic single-trader iteration** and adopt a cluster-strategy architecture. An abstract `ClusterStrategy` base class let us ship ten concrete cluster-specific strategies in parallel with isolated state, then compose them in a master `Trader`. We could iterate on the SNACKPACK pair-trader without risking the OXYGEN_SHAKE quoter.

The single highest-impact observation was that the **PEBBLES basket sum** — `XS + S + M + L + XL` — sits in the range `[49982, 50016]` with σ ≈ 2.8 on every capsule day. PEBBLES_XL had correlation between −0.7 and −0.9 against the four smaller pebbles. A dedicated `PebblesBasketArb` class took mispriced legs aggressively and posted passive offsets on the inverse, sized inside the 10-unit-per-product position limit. In hindsight, that position limit capped PEBBLES at +17,529 of live PnL — the cleanest piece of alpha in the round, but not the largest contributor.

The H5 hybrid we shipped used plain market-making on UV_VISOR, TRANSLATOR and a subset of OXYGEN_SHAKE / SLEEP_POD names, and the cluster-strategy variant on the basket-arb clusters. On the worst-day-mode capsule the hybrid backtested at +501k versus the next-best variant's +288k. The live result was even better: **+702,835**, rank **7 worldwide**. The single largest contributor was `OXYGEN_SHAKE_CHOCOLATE` at +587,831 — a plain inside-spread market-making post that absorbed the spread on a dislocated book on the live day. The strategic decision that won the round was the hybrid's choice to leave OXYGEN_SHAKE on the plain-MM variant rather than overlay a more complex strategy on top of it. The manual round added +63,933.

End of Round 5: **global position #28**, **algorithmic position #31**, **10th in Europe**, **1st in Denmark**, **Top Trader Europe**, **Top 10% Finalist**.

## What carried us through

- **Augusto's manual desk.** Without 25th-58th-69th in the first three rounds, an early exit was guaranteed.
- **Worst-day-mode discipline.** Every candidate variant had to be positive on its worst single backtest day, not on its average. This rule killed most of the literature we read and saved us from at least one variant whose paper headline numbers looked great but whose worst capsule day was deeply negative.
- **Honesty about what worked.** Most of the foreign-language literature we surveyed (Russian optimal-stopping, Japanese microstructure, French/Dutch market-making, Chinese HFT) did not ship. We kept reading anyway because the discipline of comparing competing claims sharpened our judgement on the things that did ship — Avellaneda–Stoikov, Stoikov micro-price, Huang–Lehalle–Rosenbaum, Black–Scholes, Avellaneda–Lee PCA, Lo–MacKinlay variance ratio, the Hurst exponent.
- **The community.** The Frankfurt Hedgehogs' Prosperity 3 RainforestResin pattern is the foundation of our R1 OSMIUM logic. The jmerle Prosperity 2 9th-place voucher template is the structural backbone of our R3 / R4 voucher chain. The jmerle backtester and visualiser drove every iteration in this repository.

## Reflections

We made mistakes a more experienced team would not have made: leaving HP on a fixed-FV anchor in R3, oversizing the AC_45_KO leg in the R4 manual, taking too long to abandon monolithic trader iteration. We also made decisions a more experienced team would respect: the discipline of an honest survey, the discipline of a worst-day-mode rule, the discipline of letting Augusto run the manual desk independently.

This was our first attempt. We finished 28th. The next one starts soon.
