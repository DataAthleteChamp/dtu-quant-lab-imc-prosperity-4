# Round 2 · Algorithmic

| | |
|---|---|
| Final live PnL | **+84,889** XIRECs |
| Algorithmic rank | 1,999 |
| Submitted file | [`trader.py`](trader.py) (23 KB, stdlib only) |
| Historical data used | `data/prices_round_2_day_{-1,0,1}.csv` + matching trades |

## Products

Identical to Round 1: `ASH_COATED_OSMIUM` (pegged) and `INTARIAN_PEPPER_ROOT` (drift). No new products were introduced in Round 2.

## What changed from Round 1

The Round 2 trader is a direct evolution of the Round 1 file with conservative parameter tightening:
- Two-level posting capacity split tuned from 60 / 40 to the regime where the second tier sits inside the queue.
- Inventory-skew aggression on the pegged product reduced after observing live R1 drawdowns.
- Logger output trimmed for faster simulator turn-around.

No new techniques were added to the shipped code. The full English-microstructure citation set from R1 is unchanged:

- Avellaneda & Stoikov (2008)
- Guéant & Lehalle (2012) inventory split
- Stoikov (2018) micro-price
- Huang, Lehalle & Rosenbaum (2015) Queue-Reactive Model (Chinese / French LOB calibration)
- Spokoiny LPA safe-mode guard

## What we surveyed but rejected this round

Round 2 was when we ran the four foreign-language literature reviews. Every technique was paper-traded in backtest and **all were rejected**:

- **Russian school** — Shiryaev *Optimal Stopping Rules* (1978), Peskir & Shiryaev *Free-Boundary Problems* (2006), Novikov & Shiryaev (2015) SPRT, Kabanov & Safarian *Markets with Transaction Costs* (2009), Piterbarg (1996) Gaussian extrema, Gikhman & Skorokhod (1972) SDE theory, Borodin & Salminen (2002) BM handbook. The Peskir–Shiryaev OU-exit threshold was the closest call: +128 aggregate over historical days but −41 on one binding day, so it failed our worst-day-mode rule.
- **Japanese school** — Hayashi & Yoshida (2005), Takayasu (2001+), Yura/Sornette/Takayasu (PRL 2014) Langevin OU, Kanazawa/Sueshige (PRL 2018), Kanazawa et al. (2023) non-stationary Hawkes, Mizuno/Nakano/Takayasu (2006), Mizuta/Hirano/Izumi (2020–2022) RL on Tokyo data. The Yura/Sornette OU justified our fixed FV anchor *post-hoc* but did not produce a new rule.
- **French / Dutch microstructure** — Menkveld (JFQA 2013), Menkveld & Yueshen (2019) flash crash, Van Kervel (2015–2020) order anticipation (+0.11 to +0.19 tick lift but a −1,738 backtest), Oomen (JFE 2006) U-shape variance, Boswijk HF cointegration, Hayashi–Yoshida asynchronous covariance (ρ ≈ 0.00 OSMIUM ↔ PEPPER).
- **Chinese HFT literature** — surveyed; no specific rule produced.

The full per-language inventory with the killing backtest numbers is in [`../../docs/literature_review.md`](../../docs/literature_review.md). Translating these sources gave us discipline more than alpha — but the discipline carried us through R3 and into R5.

## Reproducing the backtest

```bash
prosperity4btest cli round_2/algorithmic/trader.py 1
```

Days −1, 0, 1 are all included in `data/`.
