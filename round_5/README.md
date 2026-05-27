# Round 5 — DTU Quant Lab

| Metric | Value |
|---|---|
| Algorithmic PnL | **+702,835** XIRECs |
| Algorithmic rank | **7 worldwide** |
| Manual PnL | +63,933 (rank 985) |
| Round total | 766,769 |
| Cumulative (finals) | **897,597** |
| Global position end of round | **28** |

The comeback round. After a +3,686 algorithmic Round 3 and a +25,351 Round 4, the Round 5 algorithmic strategy returned **+702,835** — the 7th-best algorithmic score of any team in the world — vaulting us from #1,372 to #28 worldwide.

## What was traded

Round 5 expanded the market to **50 products** organised into **ten product clusters** of five symbols each:

- **PEBBLES** — five differently-sized pebbles (XS, S, M, L, XL). The basket sum is near-deterministic across days at ~50,000 with σ ≈ 2.8, with PEBBLES_XL showing strong negative correlation against the four smaller variants. The keystone alpha of the round.
- **SNACKPACK**, **MICROCHIP**, **OXYGEN_SHAKE**, **PANEL**, **UV_VISOR**, **TRANSLATOR**, **GALAXY_SOUNDS**, **ROBOT**, **SLEEP_POD** — each a five-symbol cluster with cluster-specific structure (cointegration, PCA, pair MR, basket arb, plain inside-spread MM).

Position limit was **10 units per product** across all 50 names.

The manual round was a portfolio of nine themed goods to weight between buy/sell and percentage of capital.

See [`algorithmic/`](algorithmic/) and [`manual/`](manual/).

## Result screenshot

![Round 5 detailed results](../docs/results/round_5.png)

Algorithmic PnL curve from the live submission — the smooth monotonic climb to +702,835 is the OXYGEN_SHAKE_CHOCOLATE carry compounding through the day:

![Round 5 algorithmic PnL](../docs/results/algo_round_5.png)

## What we learned

- The cluster-strategy architecture (one abstract `ClusterStrategy` base class and one concrete subclass per cluster, composed by a master `Trader`) let us ship multiple parallel strategies with isolated state — far more iteration throughput per hour than the monolithic R3/R4 file allowed.
- The bulk of the live PnL came from one product: `OXYGEN_SHAKE_CHOCOLATE` at +587,831, captured by a plain inside-spread market-making post on a dislocated live book. Cluster overlays produced small positive contributions on most other clusters; MICROCHIP residual was a net drag.
- Worst-day-mode discipline (the worst single backtest day must be positive) survived to R5 and is the reason this trader was reliable enough to finish 7th rather than 200th. We had a higher-EV variant in development that we did not ship because its worst-day backtest was negative.
- The structural observation we are most proud of is the PEBBLES basket-sum constraint (basket sum ≈ 50,000 with σ ≈ 2.8). It contributed +17,529 — capped by the 10-unit-per-product position limit — but is the cleanest piece of alpha in the round and the lesson we will carry into the next competition.

## Analysis on shipped data

<p align="center">
  <img src="../docs/plots/round_5/product_universe.png" alt="Round 5 product universe — 50 names in 10 clusters" width="92%">
</p>

50 products, colour-coded by cluster, on day-2 mid-price range. The structural variety lives in the cluster, not in the price level.

<p align="center">
  <img src="../docs/plots/round_5/pebbles_basket_constraint.png" alt="PEBBLES basket-sum constraint" width="100%">
</p>

`PEBBLES_XS + S + M + L + XL` ≈ 50,000 with σ ≈ 2.8 across 30,000 pooled ticks. The cleanest mathematical alpha in any IMC Prosperity 4 round. PEBBLES_XL has correlation −0.7 to −0.9 against the four smaller pebbles, so any breach of the constraint signals a tradeable mispricing on the inverse leg.

<p align="center">
  <img src="../docs/plots/round_5/oxygen_shake_chocolate.png" alt="OXYGEN_SHAKE_CHOCOLATE mid price" width="100%">
</p>

OXYGEN_SHAKE_CHOCOLATE — the +587,831 carry product, 84% of the round. A wide, persistent book that absorbed an inside-spread market-making post tick after tick on the live day.

<p align="center">
  <img src="../docs/plots/round_5/cluster_correlations.png" alt="Cluster-mean return correlation heatmap" width="68%">
</p>

The 10 cluster-mean returns are essentially uncorrelated. This off-diagonal independence is the structural justification for the cluster-strategy composition pattern: every cluster runs as an isolated sub-strategy with its own state, and bugs in one cluster can't bleed into another.

## In hindsight

We had a higher-EV variant in development that we did not ship because its worst-day backtest was negative — the worst-day-mode rule literally saved Round 5. If we had relaxed the rule we would have come out of the round with a much wider PnL distribution centred lower. The other regret is that we spent the first half of R5 designing the cluster framework and only the second half on alpha — if the framework had existed at the start of R3 we would have caught the HYDROGEL break before it cost us 600 places.
