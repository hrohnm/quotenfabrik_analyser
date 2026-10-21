"""Model, market and pattern tests on synthetic data (no database)."""

import numpy as np
import pandas as pd
import pytest

from quotenfabrik.analytics import evaluation as ev
from quotenfabrik.analytics.markets import GROUPS
from quotenfabrik.analytics.patterns import PatternContext, compute_patterns, wilson
from quotenfabrik.analytics.poisson import PoissonParams, fit_poisson, score_matrix
from quotenfabrik.analytics.prediction import MatchPrediction, fit_match_model
from quotenfabrik.analytics.scorers import ScorerModel

TEAMS = [1, 2, 3, 4, 5, 6]
STRENGTH = {1: 0.5, 2: 0.3, 3: 0.0, 4: 0.0, 5: -0.3, 6: -0.5}


def synthetic_matches(seasons=(2020, 2021, 2022), seed=7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows, fid = [], 1
    for season in seasons:
        start = pd.Timestamp(f"{season}-08-15", tz="UTC")
        pairs = [(h, a) for h in TEAMS for a in TEAMS if h != a]
        for k, (h, a) in enumerate(pairs):
            kickoff = start + pd.Timedelta(days=7 * (k // 3))
            lh = np.exp(0.25 + 0.25 + STRENGTH[h] - (-STRENGTH[a]) * 0.5)
            la = np.exp(0.25 + STRENGTH[a] - (-STRENGTH[h]) * 0.5)
            h1, a1 = rng.poisson(lh * 0.45), rng.poisson(la * 0.45)
            h2, a2 = rng.poisson(lh * 0.55), rng.poisson(la * 0.55)
            rows.append(
                {"fixture_id": fid, "season": season, "matchday": k // 3 + 1, "kickoff": kickoff,
                 "status": "FT", "home_id": h, "away_id": a, "hg": h1 + h2, "ag": a1 + a2,
                 "hthg": h1, "htag": a1, "hxg": np.nan, "axg": np.nan, "finished": True}
            )  # fmt: skip
            fid += 1
    df = pd.DataFrame(rows)
    df["h2g"], df["a2g"] = df["hg"] - df["hthg"], df["ag"] - df["htag"]
    return df


@pytest.fixture(scope="module")
def matches() -> pd.DataFrame:
    return synthetic_matches()


def test_score_matrix_is_a_distribution():
    m = score_matrix(1.6, 1.1, rho=-0.08)
    assert m.shape == (11, 11)
    assert abs(m.sum() - 1) < 1e-9
    assert (m >= 0).all()


def test_fit_ranks_strong_teams_higher(matches):
    model = fit_poisson(matches, pd.Timestamp("2023-06-01", tz="UTC"), PoissonParams(reg=1.0))
    strength = {t: model.attack[t] + model.defence[t] for t in TEAMS}
    assert strength[1] > strength[3] > strength[6]
    assert model.home_adv > 0


def test_no_leakage_future_results_do_not_change_predictions(matches):
    as_of = pd.Timestamp("2022-01-01", tz="UTC")
    before = fit_match_model(matches, as_of, PoissonParams(), set(TEAMS)).predict(0, 1, 6)
    changed = matches.copy()
    future = changed["kickoff"] >= as_of
    changed.loc[future, ["hg", "ag", "hthg", "htag", "h2g", "a2g"]] = [9, 0, 5, 0, 4, 0]
    after = fit_match_model(changed, as_of, PoissonParams(), set(TEAMS)).predict(0, 1, 6)
    assert (before.lh, before.la, before.lh_1h, before.la_2h) == (
        after.lh,
        after.la,
        after.lh_1h,
        after.la_2h,
    )


def test_new_team_gets_promoted_prior(matches):
    model = fit_poisson(matches, pd.Timestamp("2023-06-01", tz="UTC"), PoissonParams(), current_teams={99})
    assert 99 in model.new_teams
    assert model.attack[99] < 0 and model.defence[99] < 0


def _prediction() -> MatchPrediction:
    return MatchPrediction(1, 1, 2, 1.7, 1.1, -0.06, 0.75, 0.5, 0.95, 0.6)


def test_market_probabilities_are_consistent():
    pred = _prediction()
    probs = {p.key: p.probability for module in GROUPS.values() for p in module.probabilities(pred)}
    assert abs(probs[("1x2", "H", None)] + probs[("1x2", "D", None)] + probs[("1x2", "A", None)] - 1) < 1e-9
    for market, line in (("ou_ft", 2.5), ("ou_home", 1.5), ("ou_1h", 0.5), ("ou_away_2h", 0.5)):
        assert abs(probs[(market, "over", line)] + probs[(market, "under", line)] - 1) < 1e-9
    assert probs[("ou_ft", "over", 1.5)] > probs[("ou_ft", "over", 2.5)] > probs[("ou_ft", "over", 3.5)]
    hh = [probs[("highest_half", s, None)] for s in ("1H", "2H", "equal")]
    assert abs(sum(hh) - 1) < 1e-9
    assert probs[("dnb", "H", None)] > probs[("1x2", "H", None)]


def test_outcomes_cover_every_predicted_market(matches):
    pred = _prediction()
    m = matches.iloc[0]
    for module in GROUPS.values():
        predicted = {p.key for p in module.probabilities(pred) if p.market not in {"dc", "dnb"}}
        outcome_keys = set(module.outcomes(m).keys())
        assert predicted <= outcome_keys | {k for k in predicted if k[0] in {"dc", "dnb"}}


def test_walk_forward_uses_only_past_data(matches):
    res = ev.walk_forward(matches, [2022], PoissonParams())
    assert (
        res["as_of"] <= matches.set_index("fixture_id").loc[res["fixture_id"], "kickoff"].to_numpy()
    ).all()
    assert res["p_model"].between(0, 1).all() and res["p_base"].notna().all()
    metrics = ev.binary_metrics(res)
    assert {"brier_model", "brier_base", "brier_naive", "ece_model"} <= set(metrics.columns)


def test_wilson_interval():
    low, high = wilson(8, 10)
    assert 0.6 < low < 0.8 < high < 0.95
    assert wilson(0, 0) == (0.0, 1.0)


def test_patterns_ignore_future_matches(matches):
    as_of = pd.Timestamp("2022-01-01", tz="UTC")
    a = compute_patterns(PatternContext.build(matches, as_of), 1, 6)
    changed = matches.copy()
    changed.loc[changed["kickoff"] >= as_of, ["hg", "ag"]] = [9, 9]
    b = compute_patterns(PatternContext.build(changed, as_of), 1, 6)
    assert [(p.key, p.value, p.signal) for p in a] == [(p.key, p.value, p.signal) for p in b]
    keys = {p.key for p in a}
    assert {"home_win_rate_home", "combined_o25", "home_scored", "combined_o05_1h"} <= keys


def test_scorer_model_uses_minutes_and_lineup():
    kick = pd.Timestamp("2022-01-01", tz="UTC")
    rows = []
    for i in range(20):
        day = kick - pd.Timedelta(days=7 * (i + 1))
        rows.append((i, day, 2021, 1, 10, "Striker", "F", True, 90, 1 if i % 2 == 0 else 0, 0, 3, 2))
        rows.append((i, day, 2021, 1, 11, "Defender", "D", True, 90, 1 if i == 0 else 0, 0, 1, 0))
    players = pd.DataFrame(rows, columns=["fixture_id", "kickoff", "season", "team_id", "player_id", "name",
                                          "position", "is_starter", "minutes", "goals", "pen_goals", "shots",
                                          "shots_on"])  # fmt: skip
    matches = pd.DataFrame(
        {
            "kickoff": players["kickoff"].unique(),
            "home_id": 1,
            "away_id": 2,
            "hg": 2,
            "ag": 1,
            "finished": True,
        }
    )
    model = ScorerModel().fit(players, matches, kick)
    striker_start = model.player_lambda(10, 1, 2.0, True)
    striker_bench = model.player_lambda(10, 1, 2.0, False)
    defender = model.player_lambda(11, 1, 2.0, True)
    assert striker_start > defender > 0
    assert striker_start > 3 * striker_bench


def test_hit_rate_picks():
    from quotenfabrik.api.routers.stats import picks

    rows = [
        # 1X2: pick = H (0.5), outcome D -> miss
        (1, "1x2", "H", np.nan, 0.5, False),
        (1, "1x2", "D", np.nan, 0.3, True),
        (1, "1x2", "A", np.nan, 0.2, False),
        # O/U 2.5: pick = over (0.6), outcome over -> hit
        (1, "ou_ft", "over", 2.5, 0.6, True), (1, "ou_ft", "under", 2.5, 0.4, False),
        # single-selection market: clean sheet home 30 % -> "no" call, outcome False -> hit
        (1, "clean_sheet", "home", np.nan, 0.3, False),
    ]  # fmt: skip
    data = pd.DataFrame(rows, columns=["fixture_id", "market", "selection", "line", "probability", "outcome"])
    data["market_group"], data["season"] = "x", 2025
    result = picks(data).set_index("market")
    assert not result.loc["1x2", "hit"] and result.loc["1x2", "selection"] == "H"
    assert result.loc["ou_ft", "hit"] and result.loc["ou_ft", "pick_probability"] == 0.6
    assert (
        result.loc["clean_sheet", "hit"] and abs(result.loc["clean_sheet", "pick_probability"] - 0.7) < 1e-9
    )


def test_scorer_outcomes_with_unknown_first_scorer():
    """API data without player for the first goal: first goalscorer stays unsettled, anytime is settled."""
    from quotenfabrik.analytics.service import scorer_outcomes

    players = pd.DataFrame({"fixture_id": [1, 1, 2, 2], "player_id": [10, 11, 10, 11], "goals": [1, 0, 1, 0]})
    goals = pd.DataFrame({
        "fixture_id": [1, 1, 2],
        "player_id": [np.nan, 10.0, 10.0],
        "minute": [5, 30, 12],
        "extra_minute": [np.nan, np.nan, np.nan],
        "detail": ["Normal Goal", "Normal Goal", "Normal Goal"],
    })  # fmt: skip
    unknown = scorer_outcomes(1, players, goals)
    assert unknown[("scorer_anytime", "10", None)] is True
    assert ("scorer_first", "10", None) not in unknown
    known = scorer_outcomes(2, players, goals)
    assert known[("scorer_first", "10", None)] is True and known[("scorer_first", "11", None)] is False


def _two_league_matches(seed: int = 3) -> tuple[pd.DataFrame, dict[int, float], dict[int, int], pd.Timestamp]:
    """Two leagues of 8 teams with fixed strengths; the 2 best of league 2 and the 2 worst of league 1 swap."""
    rng = np.random.default_rng(seed)
    strength = dict(enumerate(np.linspace(0.6, -0.6, 16)))
    league_of = {t: 1 if t < 8 else 2 for t in strength}
    rows, start = [], pd.Timestamp("2021-07-01", tz="UTC")
    for season in range(3):
        for lg in (1, 2):
            teams = [t for t in strength if league_of[t] == lg]
            for h in teams:
                for a in teams:
                    if h != a:
                        lh = np.exp(0.55 + strength[h] - strength[a])
                        la = np.exp(0.3 + strength[a] - strength[h])
                        ko = start + pd.Timedelta(days=365 * season + int(rng.integers(0, 280)))
                        rows.append((len(rows), season, ko, h, a, rng.poisson(lh), rng.poisson(la), lg))
        league_of.update({6: 2, 7: 2, 8: 1, 9: 1} if season % 2 == 0 else {6: 1, 7: 1, 8: 2, 9: 2})
    m = pd.DataFrame(
        rows, columns=["fixture_id", "season", "kickoff", "home_id", "away_id", "hg", "ag", "league_id"]
    )
    m["finished"] = True
    return m, strength, league_of, start + pd.Timedelta(days=3 * 365)


def test_joint_model_without_league_column_is_unchanged():
    m, _, _, as_of = _two_league_matches()
    one = m[m["league_id"] == 1]
    params = PoissonParams(fit_rho=False)
    separate = fit_poisson(one.drop(columns="league_id"), as_of, params)
    single = fit_poisson(one, as_of, params)  # league column with a single league
    assert single.league_attack == {}
    assert np.allclose(
        [separate.attack[t] for t in separate.attack], [single.attack[t] for t in separate.attack]
    )


def test_joint_model_puts_leagues_on_one_scale():
    """League 1 teams are stronger: the joint fit ranks them above league 2 without cross-league matches."""
    m, strength, league_of, as_of = _two_league_matches()
    joint = fit_poisson(m, as_of, PoissonParams(fit_rho=False), team_league=league_of)
    net = {t: joint.attack[t] + joint.defence[t] for t in strength}
    assert joint.league_attack[1] > joint.league_attack[2]
    top_of_2, bottom_of_1 = net[10], net[5]  # not movers: only linked through the teams that swapped
    assert np.corrcoef(list(strength.values()), list(net.values()))[0, 1] > 0.9
    assert bottom_of_1 > top_of_2 or abs(bottom_of_1 - top_of_2) < 0.15
    # team without matches: level of its current league plus the promoted prior
    joint.team_league[99] = 2
    assert joint.team_attack(99) == pytest.approx(joint.league_attack[2] + joint.params.promoted_attack)


def _cup_linked_leagues(seed: int = 5) -> tuple[pd.DataFrame, dict[int, float], dict[int, int], pd.Timestamp]:
    """Two leagues (league 1 stronger) without shared teams, linked only by cup matches between them."""
    rng = np.random.default_rng(seed)
    strength = {t: (0.4 if t < 8 else -0.4) + rng.normal(0, 0.15) for t in range(16)}
    league_of = {t: 1 if t < 8 else 2 for t in strength}
    rows, start = [], pd.Timestamp("2021-07-01", tz="UTC")

    def play(h, a, lg, cup, day):
        lh = np.exp(0.55 + strength[h] - strength[a])
        la = np.exp(0.3 + strength[a] - strength[h])
        rows.append(
            (len(rows), 0, start + pd.Timedelta(days=day), h, a, rng.poisson(lh), rng.poisson(la), lg, cup)
        )

    for _rnd in range(2):
        for lg in (1, 2):
            teams = [t for t in strength if league_of[t] == lg]
            for h in teams:
                for a in teams:
                    if h != a:
                        play(h, a, lg, False, int(rng.integers(0, 280)))
    for _ in range(60):  # cup: league 1 vs league 2
        h, a = int(rng.integers(0, 8)), int(rng.integers(8, 16))
        if rng.random() < 0.5:
            h, a = a, h
        play(h, a, 99, True, int(rng.integers(0, 280)))
    cols = ["fixture_id", "season", "kickoff", "home_id", "away_id", "hg", "ag", "league_id", "cup"]
    m = pd.DataFrame(rows, columns=cols)
    m["finished"], m["neutral"] = True, False
    return m, strength, league_of, start + pd.Timedelta(days=300)


def test_cup_matches_link_leagues_without_own_level():
    m, strength, league_of, as_of = _cup_linked_leagues()
    params = PoissonParams(fit_rho=False)
    with_cup = fit_poisson(m, as_of, params, team_league=league_of)
    without = fit_poisson(m[~m["cup"]], as_of, params, team_league=league_of)
    assert set(with_cup.league_attack) == {1, 2}  # the cup (99) is not a league level
    gap = lambda f: (f.league_attack[1] + f.league_defence[1]) - (f.league_attack[2] + f.league_defence[2])  # noqa: E731
    assert gap(with_cup) > 0.3 > abs(gap(without))  # only the cup matches reveal that league 1 is stronger
    # cross-league prediction: strong team of league 1 at home against league 2 team
    lh, la = with_cup.lambdas(0, 8, cup=True)
    lh0, la0 = without.lambdas(0, 8, cup=True)
    assert lh / la > lh0 / la0


def test_neutral_venue_and_cup_home_advantage():
    m, _, league_of, as_of = _cup_linked_leagues()
    shared = fit_poisson(m, as_of, PoissonParams(fit_rho=False, cup_home_adv=False), team_league=league_of)
    assert shared.home_adv_cup is None
    lh, la = shared.lambdas(0, 1, cup=True, neutral=True)
    lh_rev, la_rev = shared.lambdas(1, 0, cup=True, neutral=True)
    assert lh == pytest.approx(la_rev) and la == pytest.approx(lh_rev)  # no home advantage on neutral ground
    own = fit_poisson(m, as_of, PoissonParams(fit_rho=False, cup_home_adv=True), team_league=league_of)
    assert own.home_adv_cup is not None
    assert own.lambdas(0, 1, cup=True)[0] / own.lambdas(0, 1)[0] == pytest.approx(
        np.exp(own.home_adv_cup - own.home_adv)
    )


def test_shots_blend_targets():
    from quotenfabrik.analytics.poisson import _with_shots

    train = pd.DataFrame({"hg": [2.0, 0.0, 1.0], "ag": [0.0, 1.0, 1.0], "hst": [6.0, 2.0, np.nan],
                          "ast": [2.0, 4.0, np.nan]})  # fmt: skip
    w = np.ones(3)
    params = PoissonParams(shots_weight=0.5, shots_mode="on_target")
    yh, ya = _with_shots(train, train["hg"].to_numpy(), train["ag"].to_numpy(), w, params, "hg", "ag")
    rate = (2 + 0 + 0 + 1) / (6 + 2 + 2 + 4)  # goals per shot on target of the matches with shot data
    assert yh[0] == pytest.approx(0.5 * 2 + 0.5 * rate * 6)
    assert ya[1] == pytest.approx(0.5 * 1 + 0.5 * rate * 4)
    assert yh[2] == 1.0 and ya[2] == 1.0  # no shot data: goals unchanged
    # total of the blended targets stays at the level of the goals (rate from the same matches)
    assert yh[:2].sum() + ya[:2].sum() == pytest.approx(3.0)


def test_shots_weight_zero_leaves_model_unchanged():
    m = synthetic_matches()
    as_of = m["kickoff"].max() + pd.Timedelta(days=1)
    rng = np.random.default_rng(3)
    m = m.assign(hst=rng.integers(1, 9, len(m)).astype(float), ast=rng.integers(1, 9, len(m)).astype(float))
    a = fit_poisson(m, as_of, PoissonParams(shots_weight=0.0))
    b = fit_poisson(m, as_of, PoissonParams(shots_weight=0.0, shots_mode="all"))
    assert a.attack == b.attack
    c = fit_poisson(m, as_of, PoissonParams())  # default: shots on target, weight 0.25
    assert c.attack != a.attack
