import argparse
import itertools as it
import random
import time
from functools import partial
from multiprocessing import Pool

from tqdm import tqdm

from db import DB, IDENTICAL_MARKETS
from manifoldpy import api
from utils import *

API_KEY, USER_ID = load_config()

# Idea:
# Write a tool that takes groups of markets with identical outcome
# and arbitrages between them.

# Specification:
# Start with only groups of two markets.
# These two markets have different probabilities for the same outcome.
# Bet only if the difference is larger than a certain margin (-m --margin).
# Simple version:
#   - Find the integer midpoint between the two probabilities and just limit bet both markets to that.
#   - This should make money on average but can be negative expected value if both probabilities are just wrong:
#     - e.g., lo_p is 0.7 and hi_p is 0.8, but true_p is 0.4.
# Complex version:
#   - Calculate the returns for each bet and calibrate them simulataneously s.t. there really is a "free lunch", i.e., a >= 0 payout in both cases.

# Implementation:


def calc_bet_amount(base_amount: int, p: float, o: str) -> int:
    """Calculates the bet amount for a given base amount, probability and outcome."""
    p_bet_successful = p if o == "YES" else 1 - p
    return round(base_amount * p_bet_successful)


def bet_on_group_simple(
    group_name, group_markets, margin, wrapper, q_filter, amount, balance, min_bet, dry_run, sleep, verbose, is_complementary=False
):
    """Bets on a group of markets with identical or complementary outcomes.
    In case of complementary outcomes, we operate do the computation (of the limit price) in the probability space
    of market 1 and convert it to the complementary probability for betting.
    """
    already_printed = False
    mkt_id_1, mkt_id_2 = group_markets
    mkt_1, mkt_2 = get_market_from_manifold(mkt_id_1), get_market_from_manifold(mkt_id_2)

    now_mani = now()
    resolved_markets = read_resolved_markets()
    if mkt_1.id in resolved_markets or mkt_2.id in resolved_markets:
        return None
    if mkt_1.isResolved or mkt_2.isResolved or mkt_1.closeTime < now_mani or mkt_2.closeTime < now_mani:
        if mkt_1.isResolved:
            print(f"Market {mkt_id_1} ({mkt_1.question}) closed/resolved. Skipping and adding to resolved list.")
            append_resolved_market(mkt_id_1)
        if mkt_2.isResolved:
            print(f"Market {mkt_id_2} ({mkt_2.question}) closed/resolved. Skipping and adding to resolved list.")
            append_resolved_market(mkt_id_2)
        return None  # skip this bet
    q_1, q_2 = mkt_1.question, mkt_2.question
    if q_filter and not (filter_question(q_1, q_filter) or filter_question(q_2, q_filter)):  # either must fit
        # print(f"Skipping {q_1} and {q_1} because they don't fit the filter: {q_filter}.")
        return None  # skip this bet

    mkt_p_1, mkt_p_2 = mkt_1.probability, mkt_2.probability
    if is_complementary:
        mkt_p_2 = 1 - mkt_p_2
    diff = abs(mkt_p_1 - mkt_p_2)
    mkt_1_is_higher = mkt_p_1 > mkt_p_2
    if mkt_1_is_higher:
        lo_mkt, hi_mkt = mkt_2, mkt_1
        lo_p, hi_p = mkt_p_2, mkt_p_1
        limit_price_hi = limit_price_mkt_1 = limit_price_arb(lo_p, hi_p)  # this needs to be in P-space 1
        limit_price_lo = limit_price_mkt_2 = 1 - limit_price_hi if is_complementary else limit_price_hi
    else:
        lo_mkt, hi_mkt = mkt_1, mkt_2
        lo_p, hi_p = mkt_p_1, mkt_p_2
        limit_price_lo = limit_price_mkt_1 = limit_price_arb(lo_p, hi_p)  # this needs to be in P-space 1
        limit_price_hi = limit_price_mkt_2 = 1 - limit_price_lo if is_complementary else limit_price_lo
    midpoint = (lo_p + hi_p) / 2

    cq_1, cq_2 = minimal_question(mkt_1.question), minimal_question(mkt_2.question)
    if verbose:
        print(f"Group: {group_name}")
        print(f"q: {cq_1:>44} | p_mkt: {mkt_p_1*100:6.1f} %")
        print(f"q: {cq_2:>44} | p_mkt: {mkt_p_2*100:6.1f} %")
        print(f"diff: {diff*100:21.1f} % | midpt: {midpoint*100:6.1f} % | limit: {limit_price_mkt_1*100:6.1f} %\n")
        if is_complementary:
            print(f"Market is complementary. | limit mkt_1: {limit_price_mkt_1*100:6.1f} % | limit mkt_2: {limit_price_mkt_2*100:6.1f} %\n")
        already_printed = True

    if diff < margin:
        return None  # skip this bet

    lo_o, hi_o = binary_outcome(lo_p, limit_price_lo), binary_outcome(hi_p, limit_price_hi)
    if not limit_price_is_between_ps(lo_p, hi_p, limit_price_mkt_1):
        return None  # skip this bet

    bet_amount_lo, bet_amount_hi = min(calc_bet_amount(base_amount=amount, p=lo_p, o=lo_o), int(balance / 2)), min(
        calc_bet_amount(base_amount=amount, p=hi_p, o=hi_o), int(balance / 2)
    )
    if not already_printed:
        print(f"Group: {group_name}")
        print(f"q: {cq_1:>44} | p_mkt: {mkt_p_1*100:6.1f} %")
        print(f"q: {cq_2:>44} | p_mkt: {mkt_p_2*100:6.1f} %")
        print(f"diff: {diff*100:21.1f} % | midpt: {midpoint*100:6.1f} % | limit: {limit_price_mkt_1*100:6.1f} %\n")
        if is_complementary:
            print(f"Market is complementary. | limit mkt_1: {limit_price_mkt_1*100:5.1f} % | limit mkt_2: {limit_price_mkt_2*100:.1f} %\n")
    if bet_amount_lo < min_bet or bet_amount_hi < min_bet:
        print(f"Bet amounts are ({bet_amount_lo}, {bet_amount_hi}) which are below the minimum bet amount of {min_bet}.")
        print("-" * 10)
        return None  # skip this bet

    lo_fn = partial(
        make_bet_and_cancel,
        wrapper=wrapper,
        amount=bet_amount_lo,
        contract_id=lo_mkt.id,
        binary_outcome=lo_o,
        limit_p=limit_price_lo,
        dry_run=dry_run,
    )
    hi_fn = partial(
        make_bet_and_cancel,
        wrapper=wrapper,
        amount=bet_amount_hi,
        contract_id=hi_mkt.id,
        binary_outcome=hi_o,
        limit_p=limit_price_hi,
        dry_run=dry_run,
    )
    with Pool(2) as p:
        res_lo = p.apply_async(lo_fn)
        res_hi = p.apply_async(hi_fn)
        p.close()
        p.join()
    success = res_hi or res_lo
    if success:
        balance = get_balance()
        print(f"New balance: {balance:.0f} M")
        if balance < 1:
            print("========================================")
            print("Balance too low. Return.")
            return False  # end all betting
        print("-" * 10)

    if sleep > 0:
        time.sleep(sleep)
    return True


def get_groups(ignore_db=True):
    """Returns a list of groups of markets with identical outcomes."""
    groups = get_groups_from_db(IDENTICAL_MARKETS)
    if not ignore_db:
        groups.update(get_groups_from_db(DB))
    return groups


def get_groups_from_db(database):
    """Returns a list of groups of markets with identical outcomes."""
    groups = dict()
    id_groups = set(mkt_dict["group"].replace("!", "") for mkt_dict in database.values() if mkt_dict["group"] is not None)
    for group in id_groups:
        if group is not None:  # filters where no group exists
            for group_name, group_markets, is_complementary in create_groups_from_str(group, database):
                if group_name is not None:  # filters where a group exists but no pairs are possible
                    groups[group_name] = group_markets, is_complementary
    assert not any(len(group_markets) != 2 for group_markets in groups.values())
    assert not any(group_name.startswith("None") for group_name in groups.keys()), f"None in group name: {groups}"
    return groups


# TODO: handle markets with complementary outcomes: (see branch)
# - convert the complementary outcome (!) to the same outcome as the other market
# - then calculate the limit price as usual
# - then convert the limit price back to the complementary outcome
# - then bet on the complementary outcome
# example:
#  - market 1: group "foo", mkt_p_1 0.78
#  - market 2: group "!foo", mkt_p_2 0.40
#  - then clearly there is a mismatch because 0.78 + 0.40 = 1.18 > 1
#  - algo:
#   1. convert "!foo" to "foo": mkt_p_2_ = 1 - 0.40 = 0.60
#   2. calculate limit price: limit_price_mkt_1 = limit_price_arb(0.78 + 0.60) = 0.69
#   3. convert limit price back to "!foo": l_ = 1 - 0.69 = 0.31
#   4. bet on "!foo" with limit price 0.31 (bet down: "NO")
#   5. bet on "foo" with limit price 0.69 (also bet down: "NO")
# This works, but I need a flag for each market within a group to indicate whether the outcome is complementary or not.
# So I need to change the data structure for a group to a tuple like this:
# (group_name, [(mkt_id, is_complementary), (mkt_id, is_complementary), ...]
# Note: I can reuse the existing functionaly and build a wrapper that finds the complementary group name
# and then creates a new data type for groups that contain complementary outcomes.


def create_complementary_groups(group: GroupName):
    pass


def parse_group_of_two_mkts(two_mkts: List[Tuple[str, bool]]) -> bool:
    (mkt_id_1, has_exclamation_1), (mkt_id_2, has_exclamation_2) = two_mkts
    is_complementary = has_exclamation_1 != has_exclamation_2
    return [mkt_id_1, mkt_id_2], is_complementary


def create_groups_from_str(group: GroupName, database: dict) -> Tuple[GroupName, Iterable[MarketId], IsComplementary]:
    """Yields groups in sets of two markets that predict identical or complementary outcomes."""
    random_number = random.random()
    if group is None:
        yield None, None, None
    resolved_markets = read_resolved_markets()
    group_mkt_collection: List[Tuple[str, bool]] = []
    for mkt_id, mkt_dict in database.items():
        if (
            mkt_dict["group"] == group
            or mkt_dict["group"] == f"!{group}"
            and mkt_id not in resolved_markets
            and not random_number > database[mkt_id]["bet_p"]
        ):
            has_exclamation = mkt_dict["group"].startswith("!")
            group_mkt_collection.append((mkt_id, has_exclamation))
    if len(group_mkt_collection) < 2:
        yield None, None, None
    elif len(group_mkt_collection) > 2:  # add all combinations of two
        combinations = list(it.combinations(group_mkt_collection, 2))
        random.shuffle(combinations)
        for idx, combo in enumerate(combinations, start=1):
            group_name = f"{group} (combo {idx})"
            group_markets, is_complementary = parse_group_of_two_mkts(combo)
            yield group_name, group_markets, is_complementary
    else:
        group_name = group
        group_markets, is_complementary = parse_group_of_two_mkts(group_mkt_collection)
        yield group_name, group_markets, is_complementary


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--amount", type=int, default=10, help="Amount to bet in M. Default: 10.")
    parser.add_argument("-mb", "--min-bet", type=int, default=1, help="Minimum bet amount in M. Default: 1.")
    parser.add_argument(
        "-m", "--margin", type=float, default=1.0, help="Margin to trigger a bet in percent (use 2 for 2 % margin). Default: 1."
    )
    parser.add_argument("-r", "--repeat", type=int, default=1, help="Number of times to repeat the betting. Default: 1.")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Dry run mode (no actual bets).")
    parser.add_argument("-s", "--sleep", type=int, default=8, help="Sleep time in seconds between bets. Default: 8.")
    parser.add_argument(
        "-f",
        "--filter",
        type=str,
        default=None,
        help="Filter markets by question. Negative filter using '- {q_filter}' Default: None.",
    )
    parser.add_argument("-i", "--ignore-db", action="store_true", help="Ignore markets from DB (only from IDENTICAL_MARKETS")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode. Print also markets with no bet.")
    return parser.parse_args()


def main():
    args = parse_args()
    amount = args.amount
    min_bet = args.min_bet
    assert args.margin >= 1, f"Margin must be >= 1 % to avoid weird effects. Got {args.margin}."
    margin = args.margin / 100
    repeat = args.repeat
    dry_run = args.dry_run
    sleep = args.sleep
    q_filter = args.filter
    ignore_db = args.ignore_db
    verbose = args.verbose

    print(
        f"Settings: amount={amount} M, min_bet={min_bet} M, margin={margin*100} %, repeat={repeat}, dry_run={dry_run}, sleep={sleep} s, q_filter={q_filter}, ignore_db={ignore_db}, verbose={verbose}"
    )
    wrapper = api.APIWrapper(API_KEY)

    groups = get_groups(ignore_db=ignore_db)
    balance = get_balance()
    print(f"Balance: {balance:.0f} M")
    if balance < 1:
        print("========================================")
        print("Balance too low. Return.")
        return False  # end all betting

    for i in range(repeat):
        print("*" * 10 + f" Repeat {i+1}/{repeat} " + "*" * 10)
        for group_name, (group_markets, is_complementary) in tqdm(groups.items()):
            finished = bet_on_group_simple(
                group_name=group_name,
                group_markets=group_markets,
                margin=margin,
                wrapper=wrapper,
                q_filter=q_filter,
                amount=amount,
                balance=balance,
                min_bet=min_bet,
                dry_run=dry_run,
                sleep=sleep,
                verbose=verbose,
                is_complementary=is_complementary,
            )
            if finished is False:  # balance too low
                return


if __name__ == "__main__":
    main()
