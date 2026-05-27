# Round 5 · Algorithmic

| | |
|---|---|
| Final live PnL | **+702,835** XIRECs |
| Algorithmic rank | **7 worldwide** |
| Submitted file | [`trader.py`](trader.py) (98 KB, stdlib only) |
| Historical data used | `data/prices_round_5_day_{2,3,4}.csv` + matching trades (~110 MB) |

## Architecture

The Round 5 trader is built around a `ClusterStrategy` abstract base class. Each of the ten product clusters is handled by a concrete subclass:

| Cluster | Subclass | Approach |
|---|---|---|
| `PEBBLES` | `PebblesBasketArb` | Basket-sum arbitrage on the near-deterministic 5-leg constraint |
| `SNACKPACK` | `SnackpackPairMR` | Pair mean-reversion (CHOC ↔ VAN, RASP ↔ STRAW) with variance-ratio gate |
| `MICROCHIP` | `MicrochipPCAResid` | PCA-residual stat-arb with trimmed-mean basket and z-score MR |
| `UV_VISOR` | `UVVisorStrategy` | Cluster strategy variant — A-style plain market-making |
| `TRANSLATOR` | `TranslatorStrategy` | A-style plain market-making, ASTRO_BLACK / GRAPHITE_MIST focus |
| `OXYGEN_SHAKE` | `OxygenShakeStrategy` | A-style market-making |
| `PANEL` | `PanelStrategy` | Trimmed-mean basket-residual MR + inside-spread MM |
| `ROBOT` | `RobotStrategy` | Cluster MR |
| `GALAXY_SOUNDS` | `GalaxySoundsStrategy` | Cluster MR |
| `SLEEP_POD` | `SleepPodStrategy` | Plain MM |

A master `Trader` instantiates the variant-selected subclasses, merges their orders, and applies a final defensive per-product clip. The shipped variant is `HYBRID_VARIANT = "H5"`, an A/B hybrid that uses the plain market-making variant on UV_VISOR, TRANSLATOR and a small set of OXYGEN_SHAKE / SLEEP_POD names, and the cluster-strategy variant on the basket clusters. The H5 hybrid backtested at +501k against the next-best variant's +288k on the worst-day-mode capsule.

## Where the +702,835 actually came from

Extracted from the live submission log (`580584.json`), aggregated by cluster:

| Cluster | Live PnL |
|---|---:|
| OXYGEN_SHAKE | **+680,640** |
| PEBBLES | +17,529 |
| PANEL | +16,320 |
| UV_VISOR | +10,401 |
| GALAXY_SOUNDS | +9,152 |
| SNACKPACK | +6,870 |
| ROBOT | +2,446 |
| SLEEP_POD | −600 |
| TRANSLATOR | −3,532 |
| MICROCHIP | −36,388 |
| **Total** | **+702,835** |

The single highest-contribution product was `OXYGEN_SHAKE_CHOCOLATE` at **+587,831** — a plain inside-spread market-making post that absorbed the spread on a dislocated book on the live day. The PEBBLES basket-sum arbitrage was conceptually elegant and worked as designed (small, near-deterministic profit), but its 10-unit-per-product position limit capped it at +17,529. MICROCHIP_SQUARE alone gave back −21,827, the largest single drag.

The honest version of the comeback narrative is therefore: **a well-calibrated plain market-maker on OXYGEN_SHAKE_CHOCOLATE captured an exceptional live-day dislocation**, and the cluster-strategy overlays held the rest of the portfolio approximately neutral. The strategic decision that won Round 5 was the H5 hybrid's choice to leave OXYGEN_SHAKE on the plain-MM variant (`AStyleMMStrategy`) rather than overlay a basket strategy on top of it. The MICROCHIP residual is the position we would change in hindsight.

## The PEBBLES basket-sum observation

Even though PEBBLES contributed a small fraction of the live PnL, the underlying observation is still the round's cleanest piece of structural alpha. On capsule days 2 / 3 / 4 the **PEBBLES basket sum** (`XS + S + M + L + XL`) stays in the range `[49982, 50016]` with σ ≈ 2.8 — essentially a hard constraint. PEBBLES_XL has correlation −0.7 to −0.9 against the four smaller pebbles. The `PebblesBasketArb` class:

1. Computes the live basket sum.
2. When the sum diverges materially from 50,000, takes the mispriced legs aggressively and posts passive offsets on the inverse legs.
3. Sizes orders to respect the 10-unit-per-product position limit — which is what capped its live contribution.

## Round 5 techniques shipped in `trader.py`

| Technique | Where it lives |
|---|---|
| **Variance ratio test** (Lo–MacKinlay style) | `SnackpackPairMR._variance_ratio()` |
| **Hurst-exponent sizing gate** | `SnackpackPairMR._hurst_size_factor()` |
| **PCA-residual stat-arb** (Avellaneda–Lee 2010) | `MicrochipPCAResid` class |
| **Basket arbitrage** | `PebblesBasketArb` |
| **Trimmed-mean basket z-score MR** | All cluster strategy classes |
| **Inventory skew** | All cluster strategies (`inv_skew` parameter) |
| **EMA-based regime gate** | `SnackpackPairMR`, `AstroGraphiteStrategy` |
| **Per-cluster circuit breaker** (`peak_mtm`) | All cluster strategies |

## Papers shipped (high confidence — implementations match published technique)

| Citation | Where |
|---|---|
| Hurst (1951), Peters (1994) *Fractal Market Analysis* | Hurst sizing gate |
| Avellaneda & Lee (2010), "Statistical Arbitrage in the US Equities Market", *Quantitative Finance* 10(7) | `MicrochipPCAResid` |
| Lo & MacKinlay variance ratio test | `_variance_ratio()` |

## Papers surveyed but not shipped

Twelve techniques were workshopped in our internal R5 dossier (`B7_TECHNIQUES.md`); only the three above made it into the live trader. The rejected list — online OU MLE (Uhlenbeck & Ornstein 1930 / Hamilton 1994), Kalman dynamic beta (Kalman 1960 / Pole 2011), OU optimal exit (Peskir & Shiryaev 2006 / Leung & Li 2015), Marchenko–Pastur eigenvalue trimming (Laloux et al. 1999), copula pair trading (Liew & Wu 2013), square-root market impact (Almgren et al. 2005 / Gatheral 2010), OU-with-jumps (Cartea & Jaimungal 2015), Bayesian changepoint (Adams & MacKay 2007), Engle–Granger cointegration, Dickey–Fuller ADF — is fully documented in [`../../docs/literature_review.md`](../../docs/literature_review.md) along with the reason each was classified offline-only or rejected.

The R5 trader has no module docstring or explicit citations in code; the class and method names carry the technique attribution.

## Reproducing the backtest

```bash
prosperity4btest cli round_5/algorithmic/trader.py 4
```

Note: the R5 data files are ~36 MB each. The day-4 backtest is the most representative single-day check; appending day 3 and day 2 reproduces the worst-day-mode capsule we used to qualify candidate variants.
