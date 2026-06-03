# Round 3 · Manual challenge

| | |
|---|---|
| Final live PnL | **+78,225** XIRECs |
| Rank | **69** worldwide |
| Lead | Augusto Villoldo |

## Challenge

A sealed two-bid auction against an unknown distribution of reserve prices.
For the first bid, the guarderners sell their bio-pod to you if the bid is higher than their reserve price (which you can sell further for 920), and for the second bid, the average of the high bids of all teams is taken and we are asked to bid right above that, with a cubic penalty if we undercut the average.

For the low bid, each so called guardener has their own price (evenly distributed and at increments of 5), and you get to buy it if your bid is above their reserve price.

For the high bid, the same rules apply, but the other bids are also taken into account. 
The average of the high bids of all teams is taken and we are asked to bid right above that, with a cubic penalty if we undercut the average. 
If we are even a bit below, our PnL drops dramatically, while a bit slightly over doesn't result in a significant penalty.

## Strategy

This is another typical game theory question.

For the low bid we decided on 761. Since the sell price is 920 and the distribution of bin prices is even at increments of 5, you need to strike a balance between getting as many bins as possible (Bins where $P_{low}$ > $P_{bin}$) and making decent profit. Solving for this, we got: $P_{Low}$ = 761

From the speed distribution given after round 2, we found that there were distinct spikes every increment of 10.
Additionally, for the second bid, we decided to be conservative since being a bit too low drops our profits much more than being a bit too high.

Hence for the high bid, we decided on 856. 

We took our lessons from the previous rounds (increased bids at round numbers) and assumed that the median would be 850 (very round number which is in between the reasonable range of 800-900), bidding right above the next multiple of 5.

## Our submission

| Bid | Price | Accepted | Rejected | Buy spend | Sell revenue | PnL |
|---|---|---|---|---|---|---|
| First | 761 | 353 | 647 | 268,633 | 324,760 | +56,127 |
| Second | 856 | 400 | 600 | 342,400 | 368,000 | +22,098 |
| **Total** | | | | 611,033 | 692,760 | **+78,225** |

## Result screenshot

![Round 3 manual results](../../docs/results/manual_round_3.png)

## Lessons

- The first bid alone delivered the majority of the PnL. The structural insight was that the population's average first bid was 768 and the average second bid was 859 — bidding one tick below each mode achieves a strong fill rate without giving up edge.
- This was Augusto's third consecutive top-100 manual finish (25th → 58th → 69th). Without it, the +3,686 algorithmic round would have dropped us out of contention before R5.
