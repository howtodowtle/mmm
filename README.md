# `mmm`: A **Manifold market maker** bot

A simple market maker bot for [Manifold](https://manifold.markets/). Finds inefficiencies on [Manifold](https://manifold.markets/) and bets on them.

> NB: This is not a fully functional library but rather open sourcing a fun personal project in case anyone wants to build on this (or take individual ideas or parts). `mmm` was built iteratively while exploring Manifold and has been moving fast (with and like Manifold itself), so many functions might not work with the current version of Manifold. I stopped developing and using `mmm` when Manifold introduced a bot tax and I felt I was spending too much time on Manifold.

## Features

### Bet according to [538](https://fivethirtyeight.com/sports)'s predictions

__What?__:

- Scrapes 538's predictions for several sports
- Places bets on Manifold Markets according to those predictions
- Options:
    - bet size (use a fixed bet size or bet according to Kelly criterion)
    - avoid the tails (not much to gain)
    - maximum position size (to avoid being stuck with a large position)
    - ...

__Why?__:

Assumes that some fringe markets on Manifold are not efficient and extracts the mana gain for improving efficiency.

__How?__:

`python3 all_538.py`

### Arbitrage

__What?__:

For a set of predefined markets tracking the exact same our complementary outcomes: Bet in such a way that prices converge and you make low-risk or even risk-free mana.

__Why?__:

Free mana, market efficiency.

__How?__:

`python3 arbitrage.py`

### Random bets

__What?__:

- Finds one or more random markets
- Bets on one outcome according to existing probabilities

__Why?__:

- To test the bot
- To maintain streaks
- To harvest bonuses (e.g. for old markets or all markets of a specific user)

__How?__:

`python3 bet_random.py`


## Installation

...
- add `config.py` with your credentials