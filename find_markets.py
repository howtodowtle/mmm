import argparse
import os
from pprint import pprint

from db import DB, IDENTICAL_MARKETS
from manifoldpy import api
from utils import filter_question, three_months_ago, unpickle_something

THREE_MONTHS_AGO = three_months_ago()


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


def find_markets(query, neg_query, creator, neg_creator, include_db, markets=None, market_types=(api.BinaryMarket,), old=False):
    if markets is None:
        markets = get_all_markets()
    markets = [m for m in markets if m.resolution is None and isinstance(m, market_types)]
    if old:
        markets = [m for m in markets if m.lastUpdatedTime < THREE_MONTHS_AGO]
    if not include_db:
        markets = [m for m in markets if m.id not in DB and m.id not in IDENTICAL_MARKETS]
    if query:
        markets = [m for m in markets if filter_question(m.question, query)]
    if neg_query:
        query = "-" + neg_query
        markets = [m for m in markets if filter_question(m.question, query)]
    if creator:
        markets = [m for m in markets if creator.lower() in m.creatorUsername.lower() or creator.lower() in m.creatorName.lower()]
    if neg_creator:
        markets = [m for m in markets if creator.lower() not in m.creatorUsername.lower() and creator.lower() not in m.creatorName.lower()]
    return markets


def create_db_entries(markets):
    return {
        market.id: {
            "question": market.question,
            "mkt_fn": None,
            "bet_p": 1.0,
            "notes": None,
            "creator": f"{market.creatorName} (@{market.creatorUsername})",
            "group": None,
        }
        for market in markets
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--question", type=str, default="", help="Question part to search for.")
    parser.add_argument("-vq", "--neg-question", type=str, default="", help="Question part to avoid.")
    parser.add_argument("-c", "--creator", type=str, default="", help="Creator to search for.")
    parser.add_argument("-vc", "--neg-creator", type=str, default="", help="Creator to avoid.")
    parser.add_argument("-i", "--include-db", action="store_true", help="Include markets that are already in the DB.")

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    markets = find_markets(
        query=args.question,
        neg_query=args.neg_question,
        creator=args.creator,
        neg_creator=args.neg_creator,
        include_db=args.include_db,
    )

    db = create_db_entries(markets)

    print(f"Found {len(db)} markets.")
    pprint(db)


if __name__ == "__main__":
    main()
