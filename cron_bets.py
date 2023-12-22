#!/usr/bin/env python3
from collections import Counter

from install_if_na import install_packages_if_not_installed

install_packages_if_not_installed(["manifoldpy", "numpy"], debug=False)

import numpy as np

from manifoldpy import api
from utils import load_config

API_KEY, _ = load_config()


def test(answer_ids, answer_probs_adjusted, n=10_000, tolerance_level=0.1):
    answer_dict_adjusted = dict(zip(answer_ids, answer_probs_adjusted))
    test_counts = Counter(np.random.choice(answer_ids, size=n, p=answer_probs_adjusted))
    test_probs = {k: v / n for k, v in test_counts.items()}
    failed_str = list(
        f"{k}: {v:.2f} vs. {answer_dict_adjusted[k]:.2f} (diff: {(v/answer_dict_adjusted[k]-1)*100:.0f} %)"
        for k, v in test_probs.items()
        if v > 0.1
    )
    assert all(abs(v / answer_dict_adjusted[k] - 1) < tolerance_level for k, v in test_probs.items() if v > 0.1), failed_str


def bet_using_market_probabilities(market_id):
    market = api.get_full_market(market_id)
    answers = market.answers
    answers_filtered = list((a.get("number"), a.get("text"), a.get("probability")) for a in answers)
    answer_ids, answer_names, answer_probs = zip(*answers_filtered)
    answer_probs_adjusted = np.array(answer_probs) / sum(answer_probs)
    test(answer_ids, answer_probs_adjusted)
    outcome = np.random.choice(answer_ids, p=answer_probs_adjusted)
    print(f"Outcome: {outcome} ({answer_names[answer_ids.index(outcome)]})")
    return wrapper.make_bet(amount=1, contractId=market_id, outcome=str(outcome))


wrapper = api.APIWrapper(API_KEY)

mvp_id = "ZitCaKG82INr7ABgiPsk"
nba_id = "SRNhxwSENFdxqxZ6vuDB"

which_market = np.random.choice([mvp_id, nba_id])

bet_using_market_probabilities(which_market)


# mvp_market = api.get_full_market(mvp_id)

# answers = mvp_market.answers

# answers_filtered = list(
#     (a.get("number"), a.get("text"), a.get("probability")) for a in answers
# )
# answer_ids, answer_names, answer_probs = zip(*answers_filtered)
# answer_probs_adjusted = np.array(answer_probs) / sum(answer_probs)


# test(answer_ids, answer_probs_adjusted)

# outcome = np.random.choice(answer_ids, p=answer_probs_adjusted)
# print(f"Outcome: {outcome} ({answer_names[answer_ids.index(outcome)]})")

# res = wrapper.make_bet(amount=1, contractId=mvp_id, outcome=str(outcome))
