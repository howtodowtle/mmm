def kelly_manifold(mkt_p, true_p, max_fraction=1.0):
    """Return the fraction of the bankroll to bet.

    f = p / b - q / a,

    where:
    p is the probability of winning,
    q is the probability of losing,
    a is the payout for winning,
    b is the payout for losing.

    NB: Wikipedia defines a as b and b as a. For me it's more intuitive
    to match a to p and b to q (positive to positive, negative to negative).
    """
    if mkt_p > true_p:
        # betting NO is just like betting YES on the opposite outcome
        true_p = 1 - true_p
        mkt_p = 1 - mkt_p
    p = true_p
    q = 1 - true_p
    # incremental payout would be 1/mkt_p but bet will move the market
    # true payout is between 1/mkt_p and 1/true_p so just use a midpoint
    a = 1 / ((mkt_p + true_p) / 2)
    b = 1
    f = p / b - q / a
    return min(max_fraction, f)
