# Literature review

Every academic and competition reference behind the shipped DTU Quant Lab traders, plus the much longer list of techniques we surveyed (often in their original language) and explicitly chose not to ship. The intent of this document is intellectual honesty: most of what we read did not survive backtesting, and saying so out loud is more useful to other Prosperity teams than a citation laundry list.

## Notation

- **Shipped** means a recognisable implementation of the technique exists in the matching `round_N/algorithmic/trader.py`.
- **Surveyed** means we read the paper, sometimes drafted code, but did not ship.
- Rounds in *italics* indicate the technique was used as a sanity check (parameter inspection, statistic computation) rather than an active strategy component.

## Shipped citations

| Author(s) | Year | Reference | Rounds shipped | Where in code |
|---|---|---|---|---|
| Avellaneda & Stoikov | 2008 | *High-Frequency Trading in a Limit Order Book* (arXiv:0706.3151) | R1, R2, R3, R4 | Reservation price / inventory skew across all spot quoters |
| Stoikov | 2018 | *The Micro-Price* (SSRN 2970694) | R1, R2, R3, R4 | Spot fair-value anchor |
| Huang, Lehalle & Rosenbaum | 2015 | *Queue-Reactive Model* (arXiv:1312.0563) | R1, R2, R3, R4 | Queue-position aware quoting in LP / HP / SUGAR books |
| Guéant, Lehalle & Fernandez-Tapia | 2012–2013 | *Dealing with the Inventory Risk* | R1, R2 | Inventory-penalty term |
| Black & Scholes | 1973 | *Pricing of Options and Corporate Liabilities* | R3, R4 | Voucher chain pricing |
| Spokoiny | — | Local Polynomial Adaptation (LPA) safe-mode guard | R1–R4 | LPA-style noise floor on quote updates |
| jmerle | 2024 | IMC Prosperity 2 9th-place voucher template | R3, R4 | Voucher chain structural backbone |
| Frankfurt Hedgehogs (TimoDiehm) | 2024 | IMC Prosperity 3 2nd-place RainforestResin StaticTrader | R1–R4 | OSMIUM / pegged-spot logic |
| Gatheral (parabola variant) | 2012 | *The SVI Parametrization* (arXiv:1204.0646) | R3, R4 | IV smile fit `σ(m) = c + b·m + a·m²` |
| Hurst | 1951 | Long-term storage capacity of reservoirs | R5 | `SnackpackPairMR._hurst_size_factor()` |
| Peters | 1994 | *Fractal Market Analysis* | R5 | Hurst sizing gate context |
| Lo & MacKinlay | 1988 | Variance Ratio test | R5 | `SnackpackPairMR._variance_ratio()` |
| Avellaneda & Lee | 2010 | *Statistical Arbitrage in the US Equities Market*, *Quantitative Finance* 10(7) | R5 | `MicrochipPCAResid` class |

## Surveyed but not shipped

We catalogue these by round so future Prosperity teams can shortcut the same reading list, with a one-line rejection reason where one applies.

### Round 1 (algorithmic finals qualifier)

- Roll (1984) bid-ask bounce (JoF) — *too coarse for tick-resolution data.*
- Ho & Stoll (1981) dealer model — *predecessor of Avellaneda–Stoikov; superseded.*
- Bouchaud & Potters — square-root market impact — *impact term too small relative to Prosperity tick spreads.*
- Cont, Bouchaud-Gefen-Potters (2004) trade-sign imbalance — *Prosperity tape too discrete to fit.*
- Easley, López de Prado & O'Hara (2011) VPIN — *toxicity bucketing did not improve worst-day-mode backtests.*
- Bacry & Muzy — Hawkes endogeneity — *intractable to fit online with state budget.*
- Krugman (1991) target-zone model — *the OSMIUM peg is not a target zone in the FX sense.*

### Round 2 (foreign-language quant school review)

The Round 2 product mix (HYDROGEL_PACK, OSMIUM continuation, basket dynamics) prompted a multi-language literature scan. None of the cited authors ultimately changed the shipped trader.

- **Russian school**: Shiryaev, Peskir, Novikov, Kabanov, Piterbarg, Gikhman, Borodin, Nechaev, Zhitlukhin — *optimal stopping under measure change; intractable with our state budget.*
- **Japanese microstructure school**: Hayashi & Yoshida, Takayasu, Yura–Sornette, Kanazawa, Mizuno, Mizuta, Hirano, Ohnishi — *several papers on JPX limit-order books; Prosperity microstructure does not match Tokyo's auction mechanics.*
- **Dutch / Netherlands school**: Menkveld, Van Kervel, Oomen, Boswijk, Frijns, Zoican, Hautsch, Hasbrouck — *survey-level reading; informed our quoter sizing intuition but not the code.*
- Challet & Marsili — minority game / anti-crowd — *no obvious mapping to a 1-tick market.*
- Easley, López de Prado & O'Hara (2011) — VPIN — *re-evaluated, same conclusion as R1.*

### Round 3 (Black–Scholes voucher chain)

- Cartea & Jaimungal (2015), *Algorithmic and High-Frequency Trading* — *too broad to extract a single shippable component in the time available.*
- Sinclair — *Volatility Trading* (Wiley) — *practitioner reference; informed our IV-smile fit decision but not directly shipped.*
- Vidyamurthy (2004) — *Pairs Trading* — *no cointegrated pair in the R3 mix.*
- Gatheral (2012) full SVI — *parabola was a sufficient fit; full SVI added parameter risk.*

### Round 4 (regime detector + voucher refinements)

- Glosten & Milgrom (1985) PIN — *PIN bucketing did not improve regime detection vs our 3-state EMA.*
- Hull & White (1987) stochastic volatility — *parameterisation cost too high for marginal gain.*
- Hull (2018) *Options, Futures & Derivatives* — *desk reference, not directly shipped.*
- Cont & Kukanov (2013) optimal liquidation — *we did not have a liquidation problem; we had a quoting problem.*
- Christoffersen & Jacobs (2004) GARCH for option valuation — *too slow to update online.*

### Round 5 (cluster strategies)

Twelve techniques were workshopped; three shipped (Hurst, Lo–MacKinlay VR, Avellaneda–Lee PCA). The rejected list:

- Uhlenbeck & Ornstein (1930) / Hamilton (1994) — online OU MLE — *fit unstable on 50-product universe.*
- Kalman (1960) / Pole (2011) — Kalman dynamic beta — *beta did not change fast enough on capsule days to justify the state cost.*
- Peskir & Shiryaev (2006) / Leung & Li (2015) — OU optimal exit — *closed-form thresholds did not beat fixed z-score thresholds in backtest.*
- Marchenko & Pastur (1967) / Laloux et al. (1999) — random-matrix eigenvalue trimming — *50-product correlation matrix too small to dress meaningfully.*
- Liew & Wu (2013) — copula pair trading — *Gaussian/t-copula calibration unstable on Prosperity data.*
- Almgren et al. (2005) / Gatheral (2010) — square-root market impact — *impact negligible at 10-unit position limits.*
- Cartea & Jaimungal (2015) — risk metrics for HFT — *unimplemented after time pressure.*
- Adams & MacKay (2007) — Bayesian online changepoint detection — *false positives on the capsule days we tested.*
- Engle & Granger (1987) cointegration — *we used residual-z-score instead.*
- Dickey & Fuller (1979) ADF — *same.*

## Discord intelligence

The `DataAthleteChamp/IMC_Prosperity_discord_scraper` tool was used to aggregate hints, organiser clarifications and other teams' published bug reports from the Prosperity Discord across the campaign. Most of the resulting corpus is noise; the high-value extracts (organiser posts on tick mechanics, position-limit enforcement, the Round 5 product universe) shaped our worst-day-mode calibration even when no single message changed a line of code.

## Acknowledgements to prior-year competitors

Two prior-year open-source teams contributed structurally to our work:

- **jmerle (Jasper van Merle)** — IMC Prosperity 2, 9th place. The voucher template at `jmerle/imc-prosperity-2` is the structural backbone of our R3 / R4 voucher chain. The `imc-prosperity-3-backtester` is the tool we used to validate every iteration.
- **Frankfurt Hedgehogs (TimoDiehm)** — IMC Prosperity 3, 2nd place. The `RainforestResin` StaticTrader pattern is the foundation of our R1 OSMIUM and R2 pegged-spot logic.

Both repositories are MIT-licensed; reusing structural patterns is consistent with their published intent.
