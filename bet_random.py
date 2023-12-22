import argparse
import os
import random
import time

import numpy as np
from tqdm import tqdm

from find_markets import find_markets
from manifoldpy import api
from utils import load_config, unpickle_something

API_KEY, _ = load_config()

MARKET_TYPES = (api.BinaryMarket, api.PseudoNumericMarket, api.FreeResponseMarket, api.MultipleChoiceMarket)


def find_latest_market_file(markets_folder="data/markets"):
    files = sorted([f for f in os.listdir(markets_folder) if f.startswith("markets_") and f.endswith(".pkl")])
    if len(files) == 0:
        raise Exception("No market files found.")
    file = os.path.join(markets_folder, files[-1])
    print(f"Using {file} as market file.")
    return file


def get_all_markets(markets_folder="data/markets"):
    markets_file = find_latest_market_file(markets_folder)
    return unpickle_something(markets_file)


def get_p_dist(pool, is_free_response=False):
    answers = list(pool.keys())
    if is_free_response:
        answers.remove("0")  # don't bet on liquidity pool
    values = [pool[a] for a in answers]
    probabilities = np.array(values) / sum(values)
    return answers, probabilities


def get_random_outcome(market):
    if isinstance(market, api.BinaryMarket):
        p = market.probability
        outcome = np.random.choice(("YES", "NO"), p=(p, 1 - p))
    elif isinstance(market, api.PseudoNumericMarket):
        outcome = np.random.choice(("YES", "NO"))
    elif isinstance(market, api.FreeResponseMarket):
        answers, probabilities = get_p_dist(market.pool, is_free_response=True)
        outcome = np.random.choice(answers, p=probabilities)
    elif isinstance(market, api.MultipleChoiceMarket):
        answers, probabilities = get_p_dist(market.pool, is_free_response=False)
        outcome = np.random.choice(answers, p=probabilities)
    else:
        raise Exception(f"Unknown market type {type(market)}")
    return outcome


def single_bet(wrapper, market, amount=1):
    outcome = get_random_outcome(market)
    res = wrapper.make_bet(amount=amount, contractId=market.id, outcome=outcome)
    return res.ok, outcome


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--amount", type=float, default=1)
    parser.add_argument("-l", "--limit", type=int, default=10, help="Max number of markets to bet on. Default: 10.")
    parser.add_argument("-q", "--question", type=str, default="", help="Question part to search for.")
    parser.add_argument("-vq", "--neg-question", type=str, default="", help="Question part to avoid.")
    parser.add_argument("-c", "--creator", type=str, default="", help="Creator to search for.")
    parser.add_argument("-vc", "--neg-creator", type=str, default="", help="Creator to avoid.")
    parser.add_argument("-i", "--include-db", action="store_true", help="Include markets that are already in the DB.")
    parser.add_argument("-s", "--sleep", type=int, default=8, help="Sleep time in seconds between bets. Default: 8.")
    parser.add_argument("-o", "--old", action="store_true", help="Only bet on old markets.")

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    creator = args.creator
    amount = args.amount
    limit = args.limit
    question = args.question
    neg_question = args.neg_question
    creator = args.creator
    neg_creator = args.neg_creator
    include_db = args.include_db
    sleep = args.sleep
    old = args.old

    markets = find_markets(
        query=question,
        neg_query=neg_question,
        creator=creator,
        neg_creator=neg_creator,
        include_db=include_db,
        market_types=MARKET_TYPES,
        old=old,
    )

    wrapper = api.APIWrapper(API_KEY)
    counter = 0
    already_bet = set()
    random.shuffle(markets)
    for market in tqdm(markets[:limit]):
        success, outcome = single_bet(wrapper=wrapper, market=market, amount=amount)
        if success:
            counter += 1
            already_bet.add(market.id)
            if isinstance(market, api.BinaryMarket):
                p = market.p
                print(f"Successfully bet {amount} M on {outcome} in {market.id}: {market.question} (p={p*100:.1f} %)")
            else:
                print(f"Successfully bet {amount} M on {outcome} in {market.id}: {market.question}")
            if sleep > 0:
                time.sleep(sleep)
    print(f"Successfully bet on {counter} markets.")


if __name__ == "__main__":
    main()
