import argparse
import math
import random
import time

from tqdm import tqdm

from db import DB
from kelly import kelly_manifold
from manifoldpy import api
from utils import (
    append_resolved_market,
    binary_outcome,
    compress_sentence,
    filter_question,
    get_balance,
    get_market_from_manifold,
    get_position_value,
    get_shares,
    is_liquidating_bet,
    limit_price,
    limit_price_is_between_ps,
    load_config,
    make_bet_and_cancel,
    minimal_question,
    now,
    read_resolved_markets,
    should_bet_position,
    should_bet_probabilities,
)

API_KEY, USER_ID = load_config()


def make_all_bets(
    wrapper, amount, min_bet, margin, tail, dry_run, use_kelly, kelly_scale, sleep, q_filter, max_shares, liquidation, fast, verbose
) -> bool:
    bets_made = 0
    print("========================================")

    balance = get_balance()
    print(f"Balance: {balance:.0f} M")
    if balance < 1 and not dry_run and not verbose:
        print("========================================")
        print("Balance too low. Return.")
        return False, bets_made

    mkt_ids = list(DB.keys())
    resolved_markets = read_resolved_markets()
    mkt_ids = [m for m in mkt_ids if m not in resolved_markets]
    random.shuffle(mkt_ids)
    print(f"Found {len(mkt_ids)} markets.")
    print("-" * 10)

    for mkt_id in tqdm(mkt_ids):
        try:
            bet_p = DB[mkt_id]["bet_p"]
            random_number = random.random()
            if random_number > bet_p:
                continue
            mkt_fn = DB[mkt_id]["mkt_fn"]
            if mkt_fn is None:
                print(f"Market {mkt_id} has no mkt_fn. Skipping.")
                print("-" * 10)
                continue
            mkt = get_market_from_manifold(mkt_id)
            question = mkt.question
            if q_filter and not filter_question(question, q_filter):  # in verbose mode, still filter
                continue

            compressed_question = compress_sentence(question) if fast else minimal_question(question)

            if mkt.isResolved or mkt.closeTime < now():
                print(f"Market {mkt_id} ({compressed_question}) closed/resolved. Skipping and adding to resolved list.")
                append_resolved_market(mkt_id)
                print("-" * 10)
                continue

            mkt_p = mkt.probability
            try:
                true_p = mkt_fn()
            except Exception as e:
                print(f"Error in mkt_fn for {mkt_id} ({compressed_question}): {e}")
                continue
            diff = mkt_p - true_p
            o = binary_outcome(mkt_p, true_p)
            individual_mkt_shares, group_shares, has_group = get_shares(mkt_id=mkt_id, database=DB, user_id=USER_ID)
            is_liq_bet = is_liquidating_bet(binary_outcome=o, shares=individual_mkt_shares)
            if liquidation and not is_liq_bet and not verbose:
                continue  # skip non-liquidation bets
            l = limit_price(mkt_p, true_p, tail)
            if abs(mkt_p - l) < 0.001 and not verbose:
                continue
            if not limit_price_is_between_ps(mkt_p, true_p, l) and not verbose:
                continue

            if should_bet_probabilities(mkt_p, true_p, margin, tail) or is_liq_bet or verbose:
                if not should_bet_position(binary_outcome=o, shares=group_shares, max_shares=max_shares) and not verbose:
                    continue
                ev_true = get_position_value(individual_mkt_shares, true_p)
                ev_mkt = get_position_value(individual_mkt_shares, mkt_p)
                print(f"q: {compressed_question:>44} | p_mkt: {mkt_p*100:6.1f} % | p_tru: {true_p*100:6.1f} % | diff: {diff*100:6.1f} %")
                shares_repr = (
                    f"{individual_mkt_shares:5.0f} shares ({group_shares:5.0f} group shares)" if has_group else f"{group_shares:16.0f} shares"
                )
                print(f"pos: {shares_repr:>42} | ev_mkt: {ev_mkt:5.0f} M | ev_tru: {ev_true:5.0f} M | diff: {ev_true-ev_mkt:6.0f} M\n")
                if use_kelly:
                    f = kelly_manifold(mkt_p=mkt_p, true_p=true_p)
                    print(f"Kelly fraction to bet: {f:.2f} (scale: {kelly_scale:.2f} --> {f*kelly_scale:.2f})")
                    bet_amount = round(f * balance * kelly_scale)
                else:
                    bet_amount = min(amount, math.floor(balance))
                if bet_amount < min_bet and not verbose:
                    print(f"Bet amount is {bet_amount} < {min_bet} M (min bet). Skipping.")
                    print("-" * 10)
                    continue
                if not verbose:
                    success = make_bet_and_cancel(
                        wrapper=wrapper,
                        amount=bet_amount,
                        contract_id=mkt_id,
                        binary_outcome=o,
                        limit_p=l,
                        dry_run=dry_run,
                    )
                    if success:
                        bets_made += 1
                        balance = get_balance()
                        print(f"New balance: {balance:.0f} M")
                        if is_liq_bet and abs(individual_mkt_shares) > 10 and abs(diff) > 0.005:
                            print(f"****Position is liquidating. Sell shares all the way to {true_p*100:.1f} %.****")
                        if balance < 1:
                            print("========================================")
                            print("Balance too low. Return.")
                            return False, bets_made
                print("-" * 10)
                if sleep > 0:
                    time.sleep(sleep)
        except Exception as e:
            print(f"Error when processing market {mkt_id}: {e}")
            print("-" * 10)
    return True, bets_made


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--amount", type=int, default=10, help="Amount to bet in M. Default: 10.")
    parser.add_argument("-mb", "--min-bet", type=int, default=1, help="Minimum bet amount in M. Default: 1.")
    parser.add_argument(
        "-m", "--margin", type=float, default=2.0, help="Margin to trigger a bet in percent (use 2 for 2 % margin). Default: 2."
    )
    parser.add_argument(
        "-t",
        "--tail",
        type=float,
        default=5,
        help="Do not trade the lower and upper tails close to 0 and 100: (0 + tail, 100 - tail) %. Default: 5.",
    )
    parser.add_argument("-r", "--repeat", type=int, default=1, help="Number of times to repeat the betting. Default: 1.")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Dry run mode (no actual bets).")
    parser.add_argument("-k", "--use-kelly", action="store_true", help="Use Kelly criterion instead of fixed amount.")
    parser.add_argument("-ks", "--kelly-scale", type=float, default=0.1, help="Kelly scale factor. Default: 0.1.")
    parser.add_argument("-s", "--sleep", type=int, default=8, help="Sleep time in seconds between bets. Default: 8.")
    parser.add_argument(
        "-f",
        "--filter",
        type=str,
        default=None,
        help="Filter markets by question. Negative filter using '- {q_filter}' Default: None.",
    )
    parser.add_argument("-ms", "--max-shares", type=int, default=1_000, help="Maximum shares to hold in one market. Default: 1_000.")
    parser.add_argument("-l", "--liquidation", action="store_true", help="Make only liquidating bets.")
    parser.add_argument("-x", "--fast", action="store_true", help="Fast mode: skip markets with low volume.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode. Print also markets with no bet.")
    return parser.parse_args()


def main():
    args = parse_args()
    amount = args.amount
    min_bet = args.min_bet
    margin = args.margin / 100
    tail = args.tail / 100
    repeat = args.repeat
    dry_run = args.dry_run
    use_kelly = args.use_kelly
    kelly_scale = args.kelly_scale
    sleep = args.sleep
    q_filter = args.filter
    max_shares = args.max_shares
    liquidation = args.liquidation
    fast = args.fast
    verbose = args.verbose

    print(
        f"Settings: amount={amount} M, min_bet={min_bet} M, margin={margin*100} %, tail={tail*100} %, "
        f"repeat={repeat}, dry_run={dry_run}, use_kelly={use_kelly}, kelly_scale={kelly_scale}, sleep={sleep}, "
        f"q_filter={q_filter}, max_shares={max_shares}, liquidation={liquidation}, fast={fast}, verbose={verbose}."
    )

    wrapper = api.APIWrapper(API_KEY)

    if use_kelly:
        print("Using Kelly criterion for bet amounts.")

    for i in range(repeat):
        print("*" * 10 + f" Repeat {i+1}/{repeat} " + "*" * 10)
        finished, bets_made = make_all_bets(
            wrapper=wrapper,
            amount=amount,
            min_bet=min_bet,
            margin=margin,
            tail=tail,
            dry_run=dry_run,
            use_kelly=use_kelly,
            kelly_scale=kelly_scale,
            sleep=sleep,
            q_filter=q_filter,
            max_shares=max_shares,
            liquidation=liquidation,
            fast=fast,
            verbose=verbose,
        )
        print(f"Made {bets_made} bets.")
        if finished is False:  # balance too low
            return


if __name__ == "__main__":
    main()
