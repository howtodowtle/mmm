import bisect
import itertools as it
from typing import Iterable

import numpy as np
import requests
from bs4 import BeautifulSoup

from utils import CACHE_EXPIRY_SCRAPING, cache_with_expiry

NBA_TEAMS_538 = {  # as used by 538
    "ATL",
    "BKN",
    "BOS",
    "CHA",
    "CHI",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GS",  # NB
    "HOU",
    "IND",
    "LAC",
    "LAL",
    "MEM",
    "MIA",
    "MIL",
    "MIN",
    "NO",  # NB
    "NY",  # NB
    "OKC",
    "ORL",
    "PHI",
    "PHX",
    "POR",
    "SA",  # NB
    "SAC",
    "TOR",
    "UTA",
    "WSH",
}

LEAGUE_URLS = {
    "Bundesliga": "https://projects.fivethirtyeight.com/soccer-predictions/bundesliga/",
    "Premier League": "https://projects.fivethirtyeight.com/soccer-predictions/premier-league/",
    "La Liga": "https://projects.fivethirtyeight.com/soccer-predictions/la-liga/",
}

LEAGUE_LENGTHS = {
    "Bundesliga": 18,
    "Premier League": 20,
    "La Liga": 20,
}

CUP_URLS = {
    "Champions League": "https://projects.fivethirtyeight.com/soccer-predictions/champions-league/",
    "Europa League": "https://projects.fivethirtyeight.com/soccer-predictions/europa-league/",
    "Conference League": "https://projects.fivethirtyeight.com/soccer-predictions/europa-conference-league/",
    "MLS": "https://projects.fivethirtyeight.com/soccer-predictions/mls/",
}


@cache_with_expiry(seconds=CACHE_EXPIRY_SCRAPING, verbose=False)  # cache for this amount, otherwise call again
def get_soup(url):
    r = requests.get(url)
    return BeautifulSoup(r.text, "html.parser")


def seed_1_2_upset_23():
    return 1 - (
        get_nba_value("DEN", "make_conf_semis")
        * get_nba_value("MEM", "make_conf_semis")
        * get_nba_value("MIL", "make_conf_semis")
        * get_nba_value("BOS", "make_conf_semis")
    )


def english_team_in_cl(cup_stage: str):
    return get_cup_stage("Manchester City", "Champions League", cup_stage)


def english_team_2_oo_3(includes_all_three=True):
    win_cl = english_team_in_cl("win")
    win_el = get_cup_stage("Manchester United", "Europa League", "win")
    win_co = get_cup_stage("West Ham United", "Conference League", "win")

    win_cl_and_el = win_cl * win_el * (1 - win_co)
    win_cl_and_co = win_cl * win_co * (1 - win_el)
    win_el_and_co = win_el * win_co * (1 - win_cl)

    win_exactly_two = win_cl_and_el + win_cl_and_co + win_el_and_co

    win_exactly_three = win_cl * win_el * win_co

    if includes_all_three:
        return win_exactly_two + win_exactly_three
    else:
        return win_exactly_two


def get_position_distribution_efficient(team_name, league_name):
    """Returns a probability distribution of the team's position in the league."""
    assert league_name in LEAGUE_URLS, f"League name must be one of {LEAGUE_URLS.keys()}"
    league_soup = get_soup(LEAGUE_URLS[league_name])
    team_row = league_soup.find("tr", {"data-str": team_name})
    position_dict = get_position_dict_from_team_row(team_row)
    p_dist = np.array([position_dict[pos] for pos in sorted(position_dict)])
    assert np.isclose(sum(p_dist), 1, atol=1e-4), f"Values in distribution don't sum to 1: {p_dist}"
    return p_dist / sum(p_dist)


def analytical_who_higher(dist_hi, dist_lo):
    """Returns the probability that the first team is higher in the table (=lower number) than the second team."""
    assert len(dist_hi) == len(dist_lo), f"Distribution lengths must be equal, got {len(dist_hi)} and {len(dist_lo)}"
    outcomes = range(len(dist_hi))
    higher = sum(dist_hi[i] * dist_lo[j] for i, j in it.product(outcomes, repeat=2) if i < j)
    lower = sum(dist_hi[i] * dist_lo[j] for i, j in it.product(outcomes, repeat=2) if j < i)
    result = higher / (higher + lower)  # ignore ties, they are impossible
    return result


def who_higher(team_hi, team_lo, league_name):
    # NB: getting the distribution is slow but the simulation is fast, high n is OK (tested 1e6)
    dist_hi = get_position_distribution_efficient(team_hi, league_name)
    dist_lo = get_position_distribution_efficient(team_lo, league_name)
    return analytical_who_higher(dist_hi, dist_lo)


def get_cup_stage(team_name, cup_name, value_name):
    """only tested for champions league"""
    value_names = ("make_playoffs", "make_round_one", "last_sixteen", "quarters", "semis", "finals", "win")
    assert value_name in value_names, f"Value name must be one of {value_names}"
    assert cup_name in CUP_URLS, f"Cup name must be one of {CUP_URLS.keys()}"
    value_map = {
        "Champions League": {
            "last_sixteen": "pct border-left champ drop-4",
            "quarters": "pct champ-quarters",
            "semis": "pct champ",
            "finals": "pct champ drop-7",
            "win": "pct champ champ-win",
        },
        "Europa League": {
            "knockout": "pct border-left champ drop-3",
            "last_sixteen": "pct champ drop-4",
            "quarters": "pct champ-quarters",
            "semis": "pct champ",
            "finals": "pct champ drop-7",
            "win": "pct champ champ-win",
        },
        "Conference League": {
            # "knockout": "pct border-left champ drop-3",
            # "last_sixteen": "pct champ drop-4",
            # "quarters": "pct champ-quarters",  # untested
            "semis": "pct champ",
            "finals": "pct champ drop-7",
            "win": "pct champ champ-win",
        },
        "MLS": {
            "make_playoffs": "pct mls",
            "make_round_one": "pct drop-5 mls",
            "win": "pct mls",
        },
    }
    soup = get_soup(CUP_URLS[cup_name])
    team_row = soup.find("tr", {"data-str": team_name})
    val_to_look_up = value_map[cup_name][value_name]
    if cup_name == "MLS" and value_name == "make_playoffs":
        val = float(team_row.find_all("td", {"class": val_to_look_up})[0]["data-val"])
    elif cup_name == "MLS" and value_name == "win":
        val = float(team_row.find_all("td", {"class": val_to_look_up})[-1]["data-val"])
    else:
        val = float(team_row.find("td", {"class": val_to_look_up})["data-val"])
    assert 0 <= val <= 1, f"Value must be between 0 and 1. Received {val}."
    return val


def get_league_rel_cl_win(team_name, league_name, value_name):
    value_names = ("rel", "cl", "win")
    assert value_name in value_names, f"Value name must be one of {value_names}"
    assert league_name in LEAGUE_URLS, f"League name must be one of {LEAGUE_URLS.keys()}"
    soup = get_soup(LEAGUE_URLS[league_name])
    team_row = soup.find("tr", {"data-str": team_name})
    rel, cl, win = [float(x["data-val"]) for x in team_row.find_all("td", {"class": "pct"})]
    val = locals()[value_name]
    assert 0 <= val <= 1, f"Value must be between 0 and 1. Received {val}."
    return val


def get_position_dict_from_team_row(team_row):
    """Returns the probability of the team being in the given position."""
    position_data = team_row.find("td", {"class": "position-dist"})["data-dist"]
    position_dict = {int(p.split(":")[0]): float(p.split(":")[1]) for p in position_data.split()}
    return position_dict


def get_league_pos(team_name, league_name, positions):
    assert league_name in LEAGUE_URLS, f"League name must be one of {LEAGUE_URLS.keys()}"
    soup = get_soup(LEAGUE_URLS[league_name])
    # if positions has length 1, convert to list
    if not isinstance(positions, Iterable):
        positions = [positions]
    team_row = soup.find("tr", {"data-str": team_name})
    position_dict = get_position_dict_from_team_row(team_row)
    # return the sum of the probabilities of the positions we are interested in
    val = sum(position_dict[p] for p in positions)
    assert 0 <= val <= 1, f"Value must be between 0 and 1. Received {val}."
    return val


def find_closest_strings(input_string, string_list):
    """Returns three strings from string_list that are closest to input_string."""
    sorted_list_original = sorted(string_list, key=lambda s: s.lower())
    string_list = [s.lower() for s in string_list]
    sorted_list = sorted(string_list)
    i = bisect.bisect_left(sorted_list, input_string.lower())
    if i > 0:
        if i < len(sorted_list):
            return sorted_list_original[i - 1 : i + 2]
        else:
            return sorted_list_original[-3:]
    else:
        return sorted_list_original[:3]


def get_nba_value(team_name, value_name):
    assert (
        team_name in NBA_TEAMS_538
    ), f"Team name must fit 538 list.\
        Received {team_name}; could it be one of {find_closest_strings(team_name, NBA_TEAMS_538)}?"
    try:
        nba_url = "https://projects.fivethirtyeight.com/2023-nba-predictions"
        soup = get_soup(nba_url)
        VALUES = ("make_playoffs", "make_conf_semis", "make_conf_finals", "make_finals", "win_finals")
        assert value_name in VALUES, f"Value name must be one of {VALUES}"
        team_row = soup.find("tr", {"class": None, "data-team": team_name})  # "class": None -> ignores team rows from live games
        if team_row is None:
            team_row = soup.find("tr", {"class": "eliminated", "data-team": team_name})
        td = team_row.find("td", {"data-col": value_name})  # was data-cell until 2023_04_11
        text = td.text.strip()
        if text == "✓" or text.startswith(">"):
            return 1.0
        elif text == "—" or text.startswith("<"):
            return 0.0
        data_val = td["data-val"]
        if data_val == "null":  # reading from string
            return float(text.replace("%", "")) / 100
        else:
            val = float(data_val) * 1e-12  # * 1e-12 was changed 2023_04_11
        # if value_name == "make_playoffs":
        #     val *= 1
        # elif value_name == "make_finals":
        #     val *= 1e-12  # until shortly before playoffs
        # elif value_name == "win_finals":
        #     val *= 1e-16  # until shortly before playoffs
        assert 0 <= val <= 1, f"Value must be between 0 and 1. Received {val}."
        return val
    except Exception as e:
        print(f"Error getting value {value_name} for team {team_name}")
        print(e)
        return None


def get_nhl_value(team_name, value_name="win"):
    assert value_name in (
        "make_conf_final",
        "make_final",
        "win",
    ), f"Value name must be one of ('make_conf_final', 'make_final', 'win'), got {value_name}"
    nhl_url = "https://projects.fivethirtyeight.com/2023-nhl-predictions/"
    soup = get_soup(nhl_url)
    rows = soup.find_all("tr")
    team_row = None
    for row in rows:
        name_tag = row.find("td", {"class": "name"})
        if name_tag is None:
            continue
        if name_tag.get("data-val") == team_name.lower():
            team_row = row
            break
    if team_row is None:
        print("Row not found for team:", team_name)
        return None

    def get_value_idx(value_name):
        if value_name == "make_conf_final":
            return -3
        elif value_name == "make_final":
            return -2
        elif value_name == "win":
            return -1

    value_tag = team_row.find_all("td", {"class": "odds"})[get_value_idx(value_name)]
    value = value_tag.get("data-val")
    val = float(value)
    if val == -1.0:  # missed playoffs
        val = 0.0
    assert 0 <= val <= 1, f"Value must be between 0 and 1. Received {val}."
    return val
