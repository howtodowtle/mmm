import datetime
import math
import pickle
import string
import sys
import time
from functools import wraps
from typing import *

import nltk
import numpy as np
import yaml
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from manifoldpy import api

RESOLVED_MARKETS = "data/resolved_markets.txt"
CONFIG = "data/config.yaml"

CACHE_EXPIRY_SCRAPING = 60 * 4  # 4 minutes
CACHE_EXPIRY_MANIFOLD = 60 * 1

MarketId = NewType("MarketId", str)
GroupName = NewType("GroupName", str)
GroupEntry = Tuple[GroupName, Iterable[MarketId]]
IsComplementary = NewType("mkt_outcome_is_complementary", bool)
# GroupEntry = Tuple[GroupName, List[MarketId, IsComplementary]]]


def cache_with_expiry(seconds, verbose=False):
    def decorator(func):
        cache = {}  # (input to func) -> (time of calling, result of calling)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if the result is already in the cache and has not expired
            key = (args, tuple(kwargs.items()))
            if key in cache and time.time() - cache[key][0] < seconds:
                if verbose:
                    func_name = func.__name__
                    print(f"Cache hit for {func_name}({key}), use cached result.")
                return cache[key][1]

            # Otherwise, call the function and cache the result
            if verbose:
                func_name = func.__name__
                print(f"Cache miss for {func_name}({key}), recompute result.")
            result = func(*args, **kwargs)
            cache[key] = (time.time(), result)
            return result

        return wrapper

    return decorator


@cache_with_expiry(seconds=CACHE_EXPIRY_MANIFOLD, verbose=False)
def get_market_from_manifold(mkt_id: MarketId) -> api.Market:
    return api.get_market(mkt_id)


def sort_by_attribute(iterable, attr_name):
    """Sort an iterable of objects by an attribute."""
    return sorted(iterable, key=lambda x: getattr(x, attr_name))


def now():
    """Return the current time in Manifold time.
    NB: Manifold time = UNIX time * 1000.
    """
    return int(time.time() * 1000)


def three_months_ago():
    """Return the date three months ago in Manifold time.
    NB: Manifold time = UNIX time * 1000.
    """
    s, mi, h, mo, d = 60, 60, 24, 31, 3
    multi = 1000
    return int((time.time() - s * mi * h * mo * d) * multi)


def load_config(username="howtodowtle"):
    with open(CONFIG, "r") as file:
        config = yaml.safe_load(file)
    api_key = config[username]["api_key"]
    user_id = config[username]["user_id"]
    return api_key, user_id


def read_resolved_markets():
    """Read which market ids are already resolved from file."""
    with open(RESOLVED_MARKETS, "r") as f:
        resolved_markets = f.read().splitlines()
    return resolved_markets


def append_resolved_market(mkt_id):
    """Append a market id to the file of resolved markets."""
    with open(RESOLVED_MARKETS, "a") as f:
        f.write(f"{mkt_id}\n")


def pickle_something(obj, filename):
    with open(filename, "wb") as f:
        pickle.dump(obj, f)


def unpickle_something(filename):
    with open(filename, "rb") as f:
        return pickle.load(f)


def get_todays_date():
    """Returns today's date in the format 2022_11_28."""
    return datetime.date.today().strftime("%Y_%m_%d")


def filter_question(question, q_filter):
    """Filter a question based on a filter string.
    Splits by comma, then strips the whitespace.
    If the filter string starts with a minus, then all filters must be absent ("all", "not in" = none present).
    Otherwise, all filters must be present.
    """
    if q_filter.startswith("-"):
        filters = q_filter.replace("-", "").split(",")
        return not any(f.lower().strip() in question.lower() for f in filters)
    else:
        filters = q_filter.split(",")
        return all(f.lower().strip() in question.lower() for f in filters)


def get_balance():
    user = api.get_user_by_name("howtodowtle")
    return user.balance


def bet_using_market_probabilities(mkt_id, wrapper, amount=1):
    market = api.get_full_market(mkt_id)
    print(f"Betting on market '{market.question}'")
    answers = market.answers
    answers_filtered = list((a.get("number"), a.get("text"), a.get("probability")) for a in answers)
    answer_ids, answer_names, answer_probs = zip(*answers_filtered)
    answer_probs_adjusted = np.array(answer_probs) / sum(answer_probs)
    outcome = np.random.choice(answer_ids, p=answer_probs_adjusted)
    print(f"Bet on outcome '{answer_names[answer_ids.index(outcome)]}' at p = {answer_probs[answer_ids.index(outcome)]*100:.1f} %.")
    return wrapper.make_bet(amount=amount, contractId=mkt_id, outcome=str(outcome))


def get_shares(mkt_id, database, user_id) -> Tuple[float, float, bool]:
    has_group = database[mkt_id]["group"] is not None
    individual_mkt_shares = get_shares_individual_mkt(mkt_id=mkt_id, user_id=user_id)
    group_shares = (
        get_group_shares(mkt_id=mkt_id, individual_mkt_shares=individual_mkt_shares, database=database, user_id=user_id)
        if has_group
        else individual_mkt_shares
    )
    return individual_mkt_shares, group_shares, has_group


def get_shares_individual_mkt(mkt_id, user_id) -> float:
    # user_bets = api.get_bets(marketId=mkt_id, userId=user_id)
    user_bets = get_user_bets_custom(mkt_id=mkt_id, user_id=user_id)
    yes_shares = sum(ub.shares for ub in user_bets if ub.outcome == "YES")
    no_shares = sum(ub.shares for ub in user_bets if ub.outcome == "NO")
    return yes_shares - no_shares


def get_group_shares(mkt_id, individual_mkt_shares, database, user_id, verbose=False) -> float:
    same_outcome_mkts, opposite_outcome_mkts = find_group(mkt_id, database)
    same_outcome_shares = (
        sum(get_shares_individual_mkt(mkt_id=mid, user_id=user_id) for mid in same_outcome_mkts if mid != mkt_id) + individual_mkt_shares
    )  # addition saves one API call
    opposite_outcome_shares = sum(get_shares_individual_mkt(mkt_id=mid, user_id=user_id) for mid in opposite_outcome_mkts)
    group_shares = same_outcome_shares - opposite_outcome_shares
    if verbose:
        print(f"Group shares: {group_shares:.0f} (same: {same_outcome_shares:.0f}, opposite: {opposite_outcome_shares:.0f})")
    return group_shares


def find_group(mkt_id, database, verbose=False) -> Tuple[List[str], List[str]]:
    """Returns all the markets in the same group as the given market."""
    if verbose:
        print(f"Finding group for market {mkt_id}...")
    group = database[mkt_id]["group"]
    if group.startswith("!"):
        same_outcome_mkts = [mid for mid in database if database[mid]["group"] == group]
        opposite_outcome_mkts = [mid for mid in database if database[mid]["group"] == group[1:]]
    else:
        same_outcome_mkts = [mid for mid in database if database[mid]["group"] == group]
        opposite_outcome_mkts = [mid for mid in database if database[mid]["group"] == "!" + group]
    if verbose:
        print(f"Markets with same outcome: {[api.get_market(mid).question for mid in same_outcome_mkts]}")
        print(f"Markets with opposite outcome: {[api.get_market(mid).question for mid in opposite_outcome_mkts]}")
    return same_outcome_mkts, opposite_outcome_mkts


def condense_question(
    question, remove_punctuation=True, remove_stopwords=True, lemmatize=True, remove_vowels=False, capitalize=False, separator=" ", length=44
):
    if remove_punctuation:
        question = question.translate(str.maketrans("", "", string.punctuation))
    words = nltk.word_tokenize(question.lower())
    if remove_stopwords:
        stop_words = set(stopwords.words("english"))
        words = [word for word in words if word not in stop_words]
    if lemmatize:
        lemmatizer = WordNetLemmatizer()
        words = [lemmatizer.lemmatize(word) for word in words]
    if remove_vowels:
        words = ["".join([char for char in word if char.lower() not in ["a", "e", "i", "o", "u"]]) for word in words]
    if capitalize:
        words = [word.capitalize() for word in words]
    condensed = separator.join(words)
    if len(condensed) > length:
        condensed = condensed[:length]
    return condensed


def compress_word(word, vowels="aeiouäöü", min_vovels=0):
    """Remove vowels from word except for:
    - first and last letter
    - if the letter before or after is a vowel
    - if there not more than `min_vowels` vowels in the word
    """
    word = word.lower()
    num_vowels = sum(c in vowels for c in word)
    if num_vowels <= min_vovels:
        return word
    compressed = word[0]
    for i in range(1, len(word) - 1):  # all but first and last letter
        if word[i] in vowels:
            if word[i - 1] in vowels or word[i + 1] in vowels:
                compressed += word[i]
        else:
            compressed += word[i]
    compressed += word[-1]
    return compressed


def compress_sentence(sentence, vowels="aeiouäöü", length=44):
    s = " ".join(list(compress_word(w, vowels=vowels) for w in sentence.split()))
    if len(s) > length:
        s = s[: length - 2] + ".."
    return s


def minimal_question(question, max_length=44):
    condensed = condense_question(question, lemmatize=False, length=2 * max_length)  # nltk
    further_compressed = compress_sentence(condensed)[:max_length]  # rules
    return further_compressed


def _get_all_bets_custom(
    username: Optional[str] = None,
    userId: Optional[str] = None,
    marketId: Optional[str] = None,
    marketSlug: Optional[str] = None,
    after: int = 0,
    limit: int = sys.maxsize,
    before_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Underlying API call for `get_all_bets`."""
    bets: List[Dict[str, Any]] = []
    i = before_id
    while True:
        num_to_get = min(limit - len(bets), 1000)
        if num_to_get <= 0:
            break
        new_bets = [
            b
            for b in api._get_bets(
                limit=num_to_get,
                before=i,
                username=username,
                userId=userId,
                marketId=marketId,
                marketSlug=marketSlug,
            )
            if b["createdTime"] > after
        ]
        bets.extend(new_bets)
        if len(new_bets) < 1000:
            break
        else:
            i = bets[-1]["id"]
    # TODO: Need a better way to determine equality of bets. `id` is not sufficient
    # At least some bets have duplicate ids.
    # assert len(bets) == len({b.id for b in bets})
    return bets


@cache_with_expiry(seconds=CACHE_EXPIRY_MANIFOLD, verbose=False)
def get_user_bets_custom(
    user_id: Optional[str] = None,
    mkt_id: Optional[str] = None,
) -> List[api.Bet]:
    """Get all bets by a specific user.
    Unlike get_bets, this will get all available bets, without a limit
    on the number fetched.
    Automatically calls the bets endpoint until all data has been read.
    You must provide at least one of the arguments, otherwise the server
    will be very sad.

    Args:
        username: The user to get bets for.
        userId: The ID of the user to get bets for.
        marketId: The ID of the market to get bets for.
        marketSlug: The slug of the market to get bets for.
        after: If present, will only fetch bets created after this timestamp.
        limit: The maximum number of bets to retrieve.
        as_json: Whether to return the raw JSON response from the API.
    """
    return [
        api.weak_structure(x, api.Bet)
        for x in _get_all_bets_custom(
            userId=user_id,
            marketId=mkt_id,
        )
    ]


def should_bet_probabilities(mkt_p, true_p, margin, tail):
    assert margin >= 0.01, "Margin must be at least 1 % to avoid weird effects."
    assert tail >= 0.02, "Don't trade at the extremes."
    diff = abs(mkt_p - true_p)
    if diff < margin:  # only trade if the difference is at least the margin
        return False
    # don't trade either super low or super high probas
    # except if we're going away from 0/100 %
    tail_adjustment = 0.001  # prevents unnecessary trades (mkt_p at 0.05001, limit_price at 0.05)
    if true_p < mkt_p <= tail + tail_adjustment:
        return False
    if true_p > mkt_p >= 1 - (tail + tail_adjustment):
        return False
    return True


def should_bet_position(binary_outcome, shares, max_shares=1_000):
    if binary_outcome == "YES" and shares > max_shares:  # don't go higher up if already high
        return False
    if binary_outcome == "NO" and shares < -max_shares:  # don't go lower down if already low
        return False
    return True  # otherwise, go for it


def get_position_value(shares, probability):
    """Returns the value of the position in M.
    Can use mkt_p or true_p as probability to get manifold's or true expected value.
    """
    return probability * max(shares, 0) + (1 - probability) * max(-shares, 0)


def is_liquidating_bet(binary_outcome, shares):
    return binary_outcome == "YES" and shares < 1 or binary_outcome == "NO" and shares > 1


def limit_price(mkt_p, true_p, tail, round_to_digits=2) -> float:
    """Rounds to `round_to_digits` digits after the decimal point but in the conservative direction.
    Never goes into tails.

    NB: Currently, manifold requires round_to_digits=2 (or smaller).
    """
    if true_p < mkt_p:  # bet down
        return max(tail, math.ceil(true_p * 10**round_to_digits) / 10**round_to_digits)
    else:  # bet up
        return min(1 - tail, math.floor(true_p * 10**round_to_digits) / 10**round_to_digits)


def limit_price_arb(lo_p, hi_p, round_to_digits=2, factor=(1 - 0.44)) -> float:
    """Calculates a limit price between `lo_p` and `hi_p` that is
    somewhere in between the two but tends towards the middle probability
    that is closer to 50 % rather than the extremes (0 % or 100 %).

    `round_to_digits`: digits after the decimal point
    `factor`: how much to lean towards the "middle" probability

    NB: Currently, manifold requires round_to_digits=2 (or smaller).
    """
    assert 0 <= round_to_digits <= 2, "round_to_digits must be between 0 and 2."
    assert 0 <= factor <= 1, "Factor must be between 0 and 1."
    diff = hi_p - lo_p
    if lo_p < 0.5 < hi_p:
        price = lo_p + diff / 2
    elif lo_p <= hi_p <= 0.5:
        price = lo_p + factor * diff
    elif 0.5 <= lo_p <= hi_p:
        price = lo_p + (1 - factor) * diff  # or hi_p - factor * diff
    else:
        raise ValueError(f"Invalid limit prices: {lo_p}, {hi_p}")
    return round(price, round_to_digits)


def limit_price_is_between_ps(mkt_p, true_p, limit_price) -> bool:
    if true_p < mkt_p:  # bet down
        return true_p < limit_price < mkt_p
    else:  # bet up
        return mkt_p < limit_price < true_p


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
    print(f"Betting {amount:4} M on {binary_outcome:3} at {limit_p*100:.1f} % (mkt {contract_id}).")
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
            print(f"Bet on market {contract_id} failed.")
            return False
        r_ = wrapper.cancel_bet(bid)
        # print("Success.")
        return True
    print("Failed.")
    return False
