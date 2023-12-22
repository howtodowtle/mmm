import os

from manifoldpy import api
from utils import get_todays_date, pickle_something, unpickle_something


def convert_json_safe(json_markets):
    all_markets = []
    for x in json_markets:
        try:
            all_markets.append(api.Market.from_json(x))
        except ValueError:
            continue
    return all_markets


def get_all_markets_safe():
    json_markets = api._get_all_markets()
    return convert_json_safe(json_markets=json_markets)


def clean_up_markets(markets_folder):
    """Keep only the oldest file and the most recent three files in the markets folder.
    All files are names markets_YYYY_MM_DD.pkl. Sort by date.
    """
    files = sorted([f for f in os.listdir(markets_folder) if f.startswith("markets_") and f.endswith(".pkl")])
    files_to_delete = files[1:-3]
    for f in files_to_delete:
        os.remove(os.path.join(markets_folder, f))


def main():
    markets = get_all_markets_safe()
    today = get_todays_date()
    filename = f"data/markets/markets_{today}.pkl"
    pickle_something(markets, filename)
    unpickled_markets = unpickle_something(filename)
    assert markets == unpickled_markets, "Markets are not the same after pickling and unpickling."
    print(f"Markets saved to {filename}.")
    clean_up_markets("data/markets")


if __name__ == "__main__":
    main()
