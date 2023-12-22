import argparse
from collections import Counter

import numpy as np


def simulate_series(p_game_team_1, n, n_games=7):
    """
    Simulates a series of games between two teams.
    Best of 7.
    Returns the number of games won by team 1.
    """
    random_numbers = np.random.rand(n_games, n)
    outcomes = random_numbers < p_game_team_1
    n_wins_team_1 = np.sum(outcomes, axis=0)
    n_wins_team_2 = np.sum(1 - outcomes, axis=0)
    assert sum(n_wins_team_1 + n_wins_team_2) == n_games * n, f"n_wins_team_1: {n_wins_team_1}, n_wins_team_2: {n_wins_team_2}"
    n_wins_team_1.clip(max=n_games // 2 + 1, out=n_wins_team_1)
    n_wins_team_2.clip(max=n_games // 2 + 1, out=n_wins_team_2)
    return n_wins_team_1, n_wins_team_2


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--p-team1", type=float, default=0.5, help="Probability of team 1 winning a game")
    parser.add_argument("-n", "--n-simulations", type=int, default=10000, help="Number of series to simulate")
    parser.add_argument("-g", "--n-games", type=int, default=7, help="Number of games in a series")
    return parser.parse_args()


def print_results(games_won):
    for (n_wins_team_1, n_wins_team_2), n_series in sorted(games_won.items()):
        outcome_str = f"{n_wins_team_1}-{n_wins_team_2}"
        print(f"{outcome_str}: {n_series:5} ({n_series / sum(games_won.values()) * 100:5.2f} %)")
    series_wins_team_1_pct = (
        sum(n_series for (n_wins_team_1, n_wins_team_2), n_series in games_won.items() if n_wins_team_1 > n_wins_team_2)
        / sum(games_won.values())
        * 100
    )
    print(f"\nTeam 1 wins {series_wins_team_1_pct:5.2f} % of the series")


def main():
    args = parse_args()
    p_game_team_1 = args.p_team1
    n_series = args.n_simulations
    n_games = args.n_games
    n_wins_team_1, n_wins_team_2 = simulate_series(p_game_team_1, n_series, n_games)
    series_outcome = Counter(zip(n_wins_team_1, n_wins_team_2))
    print_results(series_outcome)


if __name__ == "__main__":
    main()
