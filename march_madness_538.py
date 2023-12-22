import argparse
import math
import random
import re
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from kelly import kelly_manifold
from manifoldpy import api
from utils import load_config

API_KEY, _ = load_config()


def sort_dict_by_value(d, reverse=False):
    return {k: v for k, v in sorted(d.items(), key=lambda item: item[1], reverse=reverse)}


DB = {
    "B8xUypH8kjSROxoegCUj": "Alabama Crimson Tide",
    "WMIQM3TDHdvayT3bw8N6": "Arizona State Sun Devils",
    "UW5DmOnYnMLv7edEX2NQ": "Arizona Wildcats",
    "76Oy6rVPaARh30AIax9m": "Arkansas Razorbacks",
    "loGCuwVFPLrSy9j7IuYY": "Auburn Tigers",
    "JtdhnL5zdTQdIgdfA2wj": "Baylor Bears",
    "yUdakKaMP4s7wuWYmAYT": "Boise State Broncos",
    "xPvfucKsYYlPadTuVyyT": "Charleston Cougars",
    "mevuLog9bmhj5P5oByMv": "Colgate Raiders",
    "wA7i1CRak0OHikKCO7Ex": "Connecticut Huskies",
    "jTgeNmhRZz3wntbqKVvY": "Creighton Bluejays",
    "hd2dxg47ez5yvkgSpbgq": "Drake Bulldogs",
    "ae3RMXk7WRem74oVb9YQ": "Duke Blue Devils",
    "iNB4r9T0eBOofj22sTny": "Fairleigh Dickinson Knights",
    "wxoDIIxedpGk63G0cBEX": "Florida Atlantic Owls",
    "fWpt6RPg1MrmpW1insxp": "Furman Paladins",
    "ZnPMtoIAHr1WGFue0nva": "Gonzaga Bulldogs",
    "zcMraMK0QkLvxYyUc1kd": "Grand Canyon Antelopes",
    "Icpg1DkqrevY4D9nNbXJ": "Houston Cougars",
    "7iB6wrYj0uVcg1tCCE98": "Howard Bison",
    "Jq1OMoVwj0wRtWO11R1I": "Illinois Fighting Illini",
    "dedxN8sl0wiBvxltrBLr": "Indiana Hoosiers",
    "HBxbCFGiX0is7YQzlchS": "Iona Gaels",
    "05VcqnRqsjG19PdWraCc": "Iowa Hawkeyes",
    "J11tzFYpBx6gx2CygY6H": "Iowa State Cyclones",
    "tFqo2MSGrOa1yOxU1YCL": "Kansas Jayhawks",
    "evCWvOremsaaKjAEtwHd": "Kansas State Wildcats",
    "nXH33FKq1kp56uzwMK3j": "Kennesaw State Owls",
    "T7nymtHhNAKRyNvRZSWi": "Kent State Golden Flashes",
    "aPGarrjI7z1qYrJxedL9": "Kentucky Wildcats",
    "JTeT9koEXlUcqup0PYTZ": "Louisiana-Lafayette Ragin' Cajuns",
    "Upmx9omyPHvsjsZqsioC": "Marquette Golden Eagles",
    "yek7ewcfPonxzGZJ1xQl": "Maryland Terrapins",
    "1U7euIQrXjhbhk54usd3": "Memphis Tigers",
    "6I4JiLzBHaGFTnBEzr7R": "Miami (FL) Hurricanes",
    "Sy03couOK7HCentr0o74": "Michigan State Spartans",
    "6FL5Si0nruOWF8H0Xvpi": "Mississippi State Bulldogs",
    "FJLxUvaqV2c3ZxYldRFQ": "Missouri Tigers",
    "qaNbarUSGWH1I2QsCUJO": "Montana State Bobcats",
    "4BQ88xCyJcX9vl4kw01A": "Nevada Wolf Pack",
    "OoDVsbljC2NQavwhPEk3": "North Carolina State Wolfpack",
    "u9b6o9gbwZzjbAl2znUV": "Northern Kentucky Norse",
    "9pPP91dZlJdDkp4HLztz": "Northwestern Wildcats",
    "s0jhZqlUbqQVt8eKYRVz": "Oral Roberts Golden Eagles",
    "qJ0PVzYkGcOQWllqbQCJ": "Penn State Nittany Lions",
    "sgYx5LHZKR5HTuYAzZ74": "Pittsburgh Panthers",
    "IWM8HAlFrM3ssd0ly9Kp": "Princeton Tigers",
    "2qdvZ2YQRpRu3MbMtUuh": "Providence Friars",
    "RcfCq62uTQiVYKMotc9p": "Purdue Boilermakers",
    "JKMaUoooWQzu1aLiYOi9": "Saint Mary's Gaels",
    "eXSA7NkCvkQ964F3FwsG": "San Diego State Aztecs",
    "nNfKVGADfcz66EGjybAO": "Southeast Missouri State Redhawks",
    "LNfuAyLGnswMxtM41wZC": "TCU Horned Frogs",
    "CtWUIbFqmsbifzY5k2ux": "Tennessee Volunteers",
    "0f1wtDinOCRoCiyHvwRr": "Texas AM Aggies",
    "sponwsgbohDPOotvSGP8": "Texas AM-Corpus Christi Islanders",
    "mlhASqlh91wSxGOOk2wz": "Texas Longhorns",
    "diAVhpKjdkpfN85HXqY0": "Texas Southern Tigers",
    "gDBJBUU73JJ7HKmcWHbJ": "UC Santa Barbara Gauchos",
    "N4vhZP56Khpx1e2KAOsP": "UCLA Bruins",
    "20YFvaODDmcHCMz7LS32": "UNC Asheville Bulldogs",
    "q3MxadO22IA3SnA1dQ9u": "USC Trojans",
    "zwWwIkGqjD3Z17rgr9xj": "Utah State Aggies",
    "3zFq8Ypzu2XKvqvInfaX": "VCU Rams",
    "gRcGALMsWPomzueSdNXC": "Vermont Catamounts",
    "mcieLow496uDbteypjoB": "Virginia Cavaliers",
    "5Py57C8D7cbE0ObaSUSL": "West Virginia Mountaineers",
    "7jEpDrceaVEfOwnKtmfP": "Xavier Musketeers",
    # not prognostic8r
    "KRJd7vVg5283cXxY4fcZ": "Connecticut Huskies",
    "sV8U6NG2Oqu0BDug90Oi": "Gonzaga Bulldogs",
    "eiVnsGJRuofRrzye6O4B": "Texas Longhorns",
    "6Y1iLb1EZIUiCII3h2PJ": "Arizona Wildcats",
    "iOZCxEzmtsN5mJS0Mf3i": "Baylor Bears",
    "vYCINwBmahCh5weentIU": "Marquette Golden Eagles",
    "MznMdUrqVmSQVNkUHBju": "Purdue Boilermakers",
    "OMmwuvf2aKvFoxDPYPh8": "UCLA Bruins",
    "didTFY29ZX8if96v6kAa": "Kansas Jayhawks",
    "2n5siCS1FOg6PYnLtxqr": "Alabama Crimson Tide",
    "UrtVHBVvSBZ8vCLHhRYj": "Houston Cougars",
}

COMBINED_IDS = {
    "byuu2TZfobKwWwIud8pT": {
        "question": "Will a team from the ACC win the NCAA Men's basketball national championship?",
        "teams": [
            # "Duke Blue Devils",
            "Miami (FL) Hurricanes",
            # "North Carolina State Wolfpack",
            # "Pittsburgh Panthers",
            # "Virginia Cavaliers",
        ],
    },
    "Vgopea81qxIn2sn5krHM": {
        "question": "Will an ACC team win the 2023 men's NCAA basketball tournament?",
        "teams": [
            # "Duke Blue Devils",
            "Miami (FL) Hurricanes",
            # "North Carolina State Wolfpack",
            # "Pittsburgh Panthers",
            # "Virginia Cavaliers",
        ],
    },
    "4QJF8flsSVyHLgpLbcSP": {
        "question": "Will a Big 12 team win the 2023 men's NCAA basketball tournament?",
        "teams": [
            "Baylor Bears",
            "Iowa State Cyclones",
            "Kansas Jayhawks",
            "Kansas State Wildcats",
            "TCU Horned Frogs",
            "Texas Longhorns",
            "West Virginia Mountaineers",
        ],
    },
    "bx22qB4eGXRX7a90oar2": {
        "question": "Will a team from the Big 12 win the NCAA Men's basketball national championship?",
        "teams": [
            "Baylor Bears",
            "Iowa State Cyclones",
            "Kansas Jayhawks",
            "Kansas State Wildcats",
            "TCU Horned Frogs",
            "Texas Longhorns",
            "West Virginia Mountaineers",
        ],
    },
    "ICjMvQ4IHsZ6ZOOV0i6X": {
        "question": "Will a team from the SEC win the NCAA Men's basketball national championship?",
        "teams": [
            "Alabama Crimson Tide",
            "Arkansas Razorbacks",
            "Auburn Tigers",
            "Kentucky Wildcats",
            "Mississippi State Bulldogs",
            "Missouri Tigers",
            "Tennessee Volunteers",
            "Texas AM Aggies",
        ],
    },
    "1INFoMUaAPx1Jrbs37J3": {
        "question": "Will a SEC team win the 2023 men's NCAA basketball tournament?",
        "teams": [
            "Alabama Crimson Tide",
            "Arkansas Razorbacks",
            "Auburn Tigers",
            "Kentucky Wildcats",
            "Mississippi State Bulldogs",
            "Missouri Tigers",
            "Tennessee Volunteers",
            "Texas AM Aggies",
        ],
    },
    "5CjDjclpSgZyo0XnNMPq": {
        "question": "Will a team from the Big Ten win the NCAA Men's basketball national championship?",
        "teams": [
            "Illinois Fighting Illini",
            "Indiana Hoosiers",
            "Iowa Hawkeyes",
            "Maryland Terrapins",
            "Michigan State Spartans",
            "Northwestern Wildcats",
            "Penn State Nittany Lions",
            "Purdue Boilermakers",
        ],
    },
    "AvCO4aWF5E5L0bcF4FYv": {
        "question": "Will a Big Ten team win the 2023 men's NCAA basketball tournament?",
        "teams": [
            "Illinois Fighting Illini",
            "Indiana Hoosiers",
            "Iowa Hawkeyes",
            "Maryland Terrapins",
            "Michigan State Spartans",
            "Northwestern Wildcats",
            "Penn State Nittany Lions",
            "Purdue Boilermakers",
        ],
    },
    "NfjI2O49TCp7mzi8t4Fy": {
        "question": "Will a WCC team win the 2023 men's NCAA basketball tournament?",
        "teams": [
            "Gonzaga Bulldogs",
            "Saint Mary's Gaels",
        ],
    },
    "s1OZ6sYGhChsUMuOH9QP": {
        "question": "Will a Pac-12 team win the 2023 men's NCAA basketball tournament?",
        "teams": [
            "Arizona State Sun Devils",
            "Arizona Wildcats",
            "UCLA Bruins",
            "USC Trojans",
        ],
    },
    "Fjz2NtUwmpRbX2QlLfr1": {
        "question": "Will an AAC team win the 2023 men's NCAA basketball tournament?",
        "teams": [
            "Houston Cougars",
            "Memphis Tigers",
        ],
    },
    "VYrFVULOdbE4iwhsBLPT": {
        "question": "Will a Big East team win the 2023 men's NCAA basketball tournament?",
        "teams": [
            # "Creighton Bluejays",
            # "Marquette Golden Eagles",
            # "Providence Friars",
            "Connecticut Huskies",
            # "Xavier Musketeers",
        ],
    },
    "lhIkdvPok1HdBZOKmfKS": {
        "question": "Will the NCAA men's basketball championship be won by the lowest seed ever this year?",
        "teams": [
            # "Arkansas Razorbacks",
            "Florida Atlantic Owls",
            # "Princeton Tigers",
            # "Fairleigh Dickinson Knights",
        ],  # 8 seeds or lower who are still in the tournament (2023-03-19)
    },
}

TEAMS_MAP_CSV = {
    "Alabama Crimson Tide": "Alabama",
    "Arizona State Sun Devils": "Arizona State",
    "Arizona Wildcats": "Arizona",
    "Arkansas Razorbacks": "Arkansas",
    "Auburn Tigers": "Auburn",
    "Baylor Bears": "Baylor",
    "Boise State Broncos": "Boise State",
    "Charleston Cougars": "College of Charleston",
    "Colgate Raiders": "Colgate",
    "Connecticut Huskies": "Connecticut",
    "Creighton Bluejays": "Creighton",
    "Drake Bulldogs": "Drake",
    "Duke Blue Devils": "Duke",
    "Fairleigh Dickinson Knights": "Fairleigh Dickinson",
    "Florida Atlantic Owls": "Florida Atlantic",
    "Furman Paladins": "Furman",
    "Gonzaga Bulldogs": "Gonzaga",
    "Grand Canyon Antelopes": "Grand Canyon",
    "Houston Cougars": "Houston",
    "Howard Bison": "Howard",
    "Illinois Fighting Illini": "Illinois",
    "Indiana Hoosiers": "Indiana",
    "Iona Gaels": "Iona",
    "Iowa Hawkeyes": "Iowa",
    "Iowa State Cyclones": "Iowa State",
    "Kansas Jayhawks": "Kansas",
    "Kansas State Wildcats": "Kansas State",
    "Kennesaw State Owls": "Kennesaw State",
    "Kent State Golden Flashes": "Kent State",
    "Kentucky Wildcats": "Kentucky",
    "Louisiana-Lafayette Ragin' Cajuns": "Louisiana-Lafayette",
    "Marquette Golden Eagles": "Marquette",
    "Maryland Terrapins": "Maryland",
    "Memphis Tigers": "Memphis",
    "Miami (FL) Hurricanes": "Miami (FL)",
    "Michigan State Spartans": "Michigan State",
    "Mississippi State Bulldogs": "Mississippi State",
    "Missouri Tigers": "Missouri",
    "Montana State Bobcats": "Montana State",
    "Nevada Wolf Pack": "Nevada",
    "North Carolina State Wolfpack": "North Carolina State",
    "Northern Kentucky Norse": "Northern Kentucky",
    "Northwestern Wildcats": "Northwestern",
    "Oral Roberts Golden Eagles": "Oral Roberts",
    "Penn State Nittany Lions": "Penn State",
    "Pittsburgh Panthers": "Pittsburgh",
    "Princeton Tigers": "Princeton",
    "Providence Friars": "Providence",
    "Purdue Boilermakers": "Purdue",
    "Saint Mary's Gaels": "Saint Mary's (CA)",
    "San Diego State Aztecs": "San Diego State",
    "Southeast Missouri State Redhawks": "Southeast Missouri State",
    "TCU Horned Frogs": "Texas Christian",
    "Tennessee Volunteers": "Tennessee",
    "Texas AM Aggies": "Texas A&M",
    "Texas AM-Corpus Christi Islanders": "Texas A&M-Corpus Christi",
    "Texas Longhorns": "Texas",
    "Texas Southern Tigers": "Texas Southern",
    "UC Santa Barbara Gauchos": "UC-Santa Barbara",
    "UCLA Bruins": "UCLA",
    "UNC Asheville Bulldogs": "North Carolina-Asheville",
    "USC Trojans": "Southern California",
    "Utah State Aggies": "Utah State",
    "VCU Rams": "Virginia Commonwealth",
    "Vermont Catamounts": "Vermont",
    "Virginia Cavaliers": "Virginia",
    "West Virginia Mountaineers": "West Virginia",
    "Xavier Musketeers": "Xavier",
}

TEAMS_MAP_WEB = {
    "Alabama Crimson Tide": "Alabama",
    "Arizona State Sun Devils": "Arizona St. ",
    "Arizona Wildcats": "Arizona",
    "Arkansas Razorbacks": "Arkansas",
    "Auburn Tigers": "Auburn",
    "Baylor Bears": "Baylor",
    "Boise State Broncos": "Boise State",
    "Charleston Cougars": "Charleston",
    "Colgate Raiders": "Colgate",
    "Connecticut Huskies": "UConn",
    "Creighton Bluejays": "Creighton",
    "Drake Bulldogs": "Drake",
    "Duke Blue Devils": "Duke",
    "Fairleigh Dickinson Knights": "F. Dickinson",
    "Florida Atlantic Owls": "Florida Atl. ",
    "Furman Paladins": "Furman",
    "Gonzaga Bulldogs": "Gonzaga",
    "Grand Canyon Antelopes": "Gr. Canyon",
    "Houston Cougars": "Houston",
    "Howard Bison": "Howard",
    "Illinois Fighting Illini": "Illinois",
    "Indiana Hoosiers": "Indiana",
    "Iona Gaels": "Iona",
    "Iowa Hawkeyes": "Iowa",
    "Iowa State Cyclones": "Iowa State",
    "Kansas Jayhawks": "Kansas",
    "Kansas State Wildcats": "Kansas State",
    "Kennesaw State Owls": "Kenn. State",
    "Kent State Golden Flashes": "Kent State",
    "Kentucky Wildcats": "Kentucky",
    "Louisiana-Lafayette Ragin' Cajuns": "La.-Lafayette",
    "Marquette Golden Eagles": "Marquette",
    "Maryland Terrapins": "Maryland",
    "Memphis Tigers": "Memphis",
    "Miami (FL) Hurricanes": "Miami",
    "Michigan State Spartans": "Michigan St. ",
    "Mississippi State Bulldogs": "Miss. State",
    "Missouri Tigers": "Missouri",
    "Montana State Bobcats": "Montana St. ",
    "Nevada Wolf Pack": "Nevada",
    "North Carolina State Wolfpack": "NC State",
    "Northern Kentucky Norse": "N. Kentucky",
    "Northwestern Wildcats": "N'western",
    "Oral Roberts Golden Eagles": "Oral Roberts",
    "Penn State Nittany Lions": "Penn State",
    "Pittsburgh Panthers": "Pittsburgh",
    "Princeton Tigers": "Princeton",
    "Providence Friars": "Providence",
    "Purdue Boilermakers": "Purdue",
    "Saint Mary's Gaels": "St. Mary's",
    "San Diego State Aztecs": "SDSU",
    "Southeast Missouri State Redhawks": "SE Mo. St. ",
    "TCU Horned Frogs": "TCU",
    "Tennessee Volunteers": "Tennessee",
    "Texas AM Aggies": "Texas A&M",
    "Texas AM-Corpus Christi Islanders": "TX A&M-CC",
    "Texas Longhorns": "Texas",
    "Texas Southern Tigers": "TXSO",
    "UC Santa Barbara Gauchos": "UCSB",
    "UCLA Bruins": "UCLA",
    "UNC Asheville Bulldogs": "UNC-Ash. ",
    "USC Trojans": "USC",
    "Utah State Aggies": "Utah State",
    "VCU Rams": "VCU",
    "Vermont Catamounts": "Vermont",
    "Virginia Cavaliers": "Virginia",
    "West Virginia Mountaineers": "W. Virginia",
    "Xavier Musketeers": "Xavier",
}


DATA_URL = "https://projects.fivethirtyeight.com/march-madness-api/2023/fivethirtyeight_ncaa_forecasts.csv"

RESOLVED_MARKETS = "resolved_markets.txt"


def read_resolved_markets():
    """Read which market ids are already resolved from file."""
    with open(RESOLVED_MARKETS, "r") as f:
        resolved_markets = f.read().splitlines()
    return resolved_markets


def append_resolved_market(mkt_id):
    """Append a market id to the file of resolved markets."""
    with open(RESOLVED_MARKETS, "a") as f:
        f.write(f"{mkt_id}\n")


def get_538_team_from_q(q):
    pattern = r"Will the (.*) win the 2023 NCAA men's 'March Madness' basketball tournament?"
    q_team = re.findall(pattern, q)[0]
    return TEAMS_MAP_CSV[q_team]


def download_data(data_url):
    """Downloads a csv file from a url and returns a pandas dataframe."""
    df = pd.read_csv(data_url, usecols=["gender", "forecast_date", "team_name", "rd7_win"])
    df = df[df.gender == "mens"]
    df["forecast_date"] = df["forecast_date"].apply(convert_str_to_date)
    df = keep_only_latest(df)
    assert len(df) == 68
    return df


def keep_only_latest(df):
    """Returns a dataframe with only the latest forecasts."""
    latest_date = df.forecast_date.max()
    print(f"Latest date: {latest_date}")
    return df[df.forecast_date == latest_date]


def check_if_less_than_one_day_old(date):
    """Returns True if the date is less than one day old."""
    now = datetime.now()
    return (now - date).days < 1


def convert_str_to_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def get_value_csv(team_538, df):
    return df.rd7_win[df.team_name == team_538].item()


def get_soup(url):
    r = requests.get(url)
    return BeautifulSoup(r.text, "html.parser")


def get_rows_selenium():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    # Start a new browser window
    driver = webdriver.Firefox()

    URL = "https://projects.fivethirtyeight.com/2023-march-madness-predictions"

    # Navigate to the page with the table
    driver.get(URL)

    # Wait for the table to load
    wait = WebDriverWait(driver, 10)
    table = wait.until(EC.presence_of_element_located((By.ID, "team-table")))

    # Extract the table data
    table_html = table.get_attribute("innerHTML")

    # Parse the table data with BeautifulSoup
    soup = BeautifulSoup(table_html, "html.parser")
    tbody = soup.find("tbody")
    rows = tbody.find_all("tr")

    # Close the browser window
    driver.quit()

    return rows


def get_value_selenium(team_web, rows):
    for row in rows:
        team_name_row = row.find("td", class_="team-name").text.strip()
        if team_web in team_name_row:
            win_pct = float(row.find("td", class_="round win-column").find("abbr")["title"].strip("%")) / 100
            return win_pct
    return None


def should_bet(mkt_p, true_p, margin, tail):
    assert margin >= 0.01, "Margin must be at least 1 % to avoid weird effects."
    assert tail >= 0.02, "Don't trade at the extremes."
    diff = abs(mkt_p - true_p)
    if diff < margin:  # only trade if the difference is at least the margin
        return False
    # don't trade either super low or super high probas
    # except if we're going away from 0/100 %
    tail_adjustment = 1e-3  # prevents unnecessary trades (mkt_p at 0.05001, limit_price at 0.05)
    if true_p < mkt_p <= tail + tail_adjustment:
        return False
    if true_p > mkt_p >= 1 - (tail + tail_adjustment):
        return False
    return True


def limit_price(mkt_p, true_p, tail):
    if true_p < mkt_p:  # bet down
        return max(tail, math.ceil(true_p * 100) / 100)
    else:  # bet up
        return min(1 - tail, math.floor(true_p * 100) / 100)


def binary_outcome(mkt_p, true_p):
    if true_p < mkt_p:  # bet down
        return "NO"
    else:  # bet up
        return "YES"


def get_bed_id(response):
    if response.status_code != 200:
        print(response.status_code, response.text)
        return None
    j = response.json()
    return j.get("betId")


def make_bet_and_cancel(wrapper, amount, contract_id, binary_outcome, limit_p, dry_run):
    print(f"Betting {amount} M on {binary_outcome} at {limit_p*100:.0f} % (market {contract_id}).")
    if dry_run:
        print("Dry run (no bet made).")
        return False
    r = wrapper.make_bet(
        amount=amount,
        contractId=contract_id,
        outcome=binary_outcome,
        limitProb=limit_p,
    )
    if r.status_code == 200:
        bid = get_bed_id(r)
        if bid is None:
            print("Failed.")
            return False
        r_ = wrapper.cancel_bet(bid)
        print("Success.")
        return True
    print("Failed.")
    return False


def make_all_bets(data, wrapper, amount, min_bet, margin, tail, dry_run, use_kelly, kelly_scale, use_csv, sleep) -> bool:
    print("========================================")

    balance = get_balance()
    print(f"Balance: {balance:.0f} M")
    if balance < 1 and not dry_run:
        print("========================================")
        print("Balance too low. Return.")
        return False

    mkt_ids = list(DB.keys()) + list(COMBINED_IDS.keys())
    resolved_markets = read_resolved_markets()
    mkt_ids = [m for m in mkt_ids if m not in resolved_markets]
    random.shuffle(mkt_ids)
    print(f"Found {len(mkt_ids)} markets.")
    print("-" * 10)

    for mkt_id in tqdm(mkt_ids):
        mkt = api.get_market(mkt_id)

        if mkt.isResolved:
            print(f"Market {mkt_id} ({mkt.question[:44]}) resolved. Skipping and adding to resolved list.")
            append_resolved_market(mkt_id)
            print("-" * 10)
            continue

        mkt_p = mkt.probability
        teams = COMBINED_IDS[mkt_id]["teams"] if mkt_id in COMBINED_IDS else [DB[mkt_id]]
        true_p_fn = get_value_csv if use_csv else get_value_selenium
        lookup_map = TEAMS_MAP_CSV if use_csv else TEAMS_MAP_WEB
        true_p = sum(true_p_fn(lookup_map[team_name], data) for team_name in teams)
        question = mkt.question

        if should_bet(mkt_p, true_p, margin, tail):
            print(f"Question: {question[:44]:44} | Market: {mkt_p*100:4.1f} % | True: {true_p*100:5.1f} % | Diff: {(mkt_p-true_p)*100:4.1f} %")
            l = limit_price(mkt_p, true_p, tail)
            o = binary_outcome(mkt_p, true_p)
            if use_kelly:
                f = kelly_manifold(mkt_p=mkt_p, true_p=true_p)
                print(f"Kelly fraction to bet: {f:.2f} (scale: {kelly_scale:.2f} --> {f*kelly_scale:.2f})")
                bet_amount = round(f * balance * kelly_scale)
            else:
                bet_amount = min(amount, math.floor(balance))
            if bet_amount < min_bet:
                print(f"Bet amount is {bet_amount} < {min_bet} M (min bet). Skipping.")
                print("-" * 10)
                continue
            success = make_bet_and_cancel(
                wrapper,
                amount=bet_amount,
                contract_id=mkt_id,
                binary_outcome=o,
                limit_p=l,
                dry_run=dry_run,
            )
            if success:
                balance = get_balance()
                print(f"New balance: {balance:.0f} M")
                if balance < 1:
                    print("========================================")
                    print("Balance too low. Return.")
                    return False
            print("-" * 10)
            if sleep > 0:
                time.sleep(sleep)
    return True


def get_balance():
    user = api.get_user_by_name("howtodowtle")
    return user.balance


def main(amount, min_bet, margin, tail, repeat, dry_run, use_kelly, kelly_scale, use_csv, sleep):
    wrapper = api.APIWrapper(API_KEY)
    if use_csv:
        print("Using CSV to get data from 538.")
        data = download_data(DATA_URL)
    else:  # use selenium
        print("Using Selenium to get data from 538.")
        data = get_rows_selenium()

    if use_kelly:
        print("Using Kelly criterion for bet amounts.")

    for i in range(repeat):
        print("*" * 10 + f" Repeat {i+1}/{repeat} " + "*" * 10)
        finished = make_all_bets(
            data=data,
            wrapper=wrapper,
            amount=amount,
            min_bet=min_bet,
            margin=margin,
            tail=tail,
            dry_run=dry_run,
            use_kelly=use_kelly,
            kelly_scale=kelly_scale,
            use_csv=use_csv,
            sleep=sleep,
        )
        if not finished:
            return


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
    parser.add_argument("-c", "--use-csv", action="store_true", help="Use CSV data instead of Selenium.")
    parser.add_argument("-s", "--sleep", type=int, default=8, help="Sleep time in seconds between bets. Default: 8.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    amount = args.amount
    min_bet = args.min_bet
    margin = args.margin / 100
    tail = args.tail / 100
    repeat = args.repeat
    dry_run = args.dry_run
    use_kelly = args.use_kelly
    kelly_scale = args.kelly_scale
    use_csv = args.use_csv
    sleep = args.sleep

    main(
        amount=amount,
        min_bet=min_bet,
        margin=margin,
        tail=tail,
        repeat=repeat,
        dry_run=dry_run,
        use_kelly=use_kelly,
        kelly_scale=kelly_scale,
        use_csv=use_csv,
        sleep=sleep,
    )
