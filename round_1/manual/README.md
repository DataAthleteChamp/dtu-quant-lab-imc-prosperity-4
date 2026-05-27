# Round 1 · Manual challenge

| | |
|---|---|
| Final live PnL | **+85,000** XIRECs |
| Rank | **25** worldwide |
| Lead | Augusto Villoldo |

## Challenge

Two tradable goods. For each, choose a single buy order at a chosen price (positive premium over reference) and a chosen volume. The Prosperity engine paid each order against an undisclosed PnL-vs-volume curve with a sawtooth shape — picking the local maximum of the curve mattered as much as picking the right price.

## Our submission

| Good | Side | Price | Volume | Result PnL |
|---|---|---|---|---|
| Dryland Flax | BUY | +30 | 9,000 | +9,000 |
| Ember Mushroom | BUY | +19 | 40,000 | +76,000 |
| **Total** | | | | **+85,000** |

Augusto's choice landed on the apex of both sawtooth functions: the Dryland Flax curve peaks at volume 9,000 and the Ember Mushroom curve peaks at volume 40,000. The +19 bid price for Ember Mushroom was the higher-PnL of the two visible plateaus.

## Result screenshot

![Round 1 manual results](../../docs/results/manual_round_1.png)

## Lessons

- For sawtooth payoff structures with undisclosed reserve curves, the modal value of the population's bid distribution is rarely the optimum. Augusto solved by exhaustively evaluating each integer volume bin against the published feedback graph.
- Volume sizing was the dominant variable; the price premium was a one-tick decision.
