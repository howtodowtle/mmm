import argparse

from manifoldpy import api
from utils import bet_using_market_probabilities, load_config

API_KEY, _ = load_config()


NBA_MKT_ID_23 = "SRNhxwSENFdxqxZ6vuDB"
NBA_MKT_ID_24 = "PnA6r86N6VTijoW44qAD"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--api_key", type=str, default=API_KEY)
    parser.add_argument("-m", "--market_id", type=str, default=NBA_MKT_ID_23)
    parser.add_argument("-a", "--amount", type=float, default=1)
    return parser.parse_args()


def main():
    args = parse_args()
    api_key = args.api_key
    mkt_id = args.market_id
    amount = args.amount

    wrapper = api.APIWrapper(api_key)
    bet_using_market_probabilities(mkt_id=mkt_id, amount=amount, wrapper=wrapper)


if __name__ == "__main__":
    main()
