"""Playing style profiles (no database)."""

import pandas as pd
import pytest

from quotenfabrik.analytics import style


def stats() -> pd.DataFrame:
    """Team 1 (possession, many shots) against teams 2..9; team 1 home in every match."""
    rows = []
    kickoff = pd.Timestamp("2026-08-01", tz="UTC")
    for i in range(8):
        fid, ko, opp = i + 1, kickoff + pd.Timedelta(days=7 * i), 2 + i
        common = {"fixture_id": fid, "kickoff": ko, "league_id": 78, "season": 2026, "home_team_id": 1,
                  "away_team_id": opp, "ft_home": 2, "ft_away": 1, "corners": 5, "fouls": 10, "cards": 2,
                  "saves": 2, "xg": None}  # fmt: skip
        rows.append({**common, "team_id": 1, "possession": 65.0, "shots": 20, "shots_on": 8, "inside": 14,
                     "passes": 600, "passes_acc": 540})  # fmt: skip
        rows.append({**common, "team_id": opp, "possession": 35.0, "shots": 5, "shots_on": 2, "inside": 3,
                     "passes": 300, "passes_acc": 240})  # fmt: skip
    return pd.DataFrame(rows)


def test_team_rows_join_opponent_and_goals():
    rows = style.team_rows(stats())
    t1 = rows[rows["team"] == 1].iloc[0]
    assert t1["gf"] == 2 and t1["ga"] == 1 and t1["shots_a"] == 5 and t1["shots_on_a"] == 2
    assert t1["xg_n"] == 0  # no xG in this match


def test_profile_ratios_from_sums():
    rows = style.team_rows(stats())
    prof = style.profiles_at(rows, pd.Timestamp("2026-12-01", tz="UTC"))
    p = prof.loc[1]
    assert p["matches"] == 8
    assert p["possession"] == pytest.approx(0.65)
    assert p["shots"] == pytest.approx(20) and p["shots_against"] == pytest.approx(5)
    assert p["conversion_on"] == pytest.approx(2 / 8)
    assert p["pass_accuracy"] == pytest.approx(0.9)
    assert p["shot_share"] == pytest.approx(0.8)
    assert pd.isna(p["xg"])
    assert 2 not in prof.index  # opponents with a single match are below MIN_MATCHES


def test_profiles_use_only_earlier_matches():
    rows = style.team_rows(stats())
    before_sixth = pd.Timestamp("2026-08-01", tz="UTC") + pd.Timedelta(days=35)
    assert style.profiles_at(rows, before_sixth).loc[1, "matches"] == 5
    rolling = style.rolling_profiles(rows)
    team = rolling[rolling["team"] == 1].set_index("fixture_id")
    assert pd.isna(team.loc[5, "shots"])  # only 4 earlier matches
    assert team.loc[6, "matches"] == 5 and team.loc[6, "shots"] == pytest.approx(20)


def test_possession_yield_relative_to_peers():
    prof = pd.DataFrame({"possession": [0.4, 0.5, 0.6, 0.7, 0.5], "shot_share": [0.4, 0.5, 0.6, 0.7, 0.6]})
    out = style.with_yield(prof)
    assert out.loc[3, "possession_yield"] < 0.02  # high possession alone is not sterile
    assert out.loc[4, "possession_yield"] > 0.05  # more shots than teams with the same possession


def test_labels():
    pct = pd.Series({"possession": 0.9, "shots": 0.9, "shots_on": 0.8, "possession_yield": 0.2,
                     "conversion_on": 0.1, "shots_against": 0.1, "shots_on_against": 0.2, "fouls": 0.5})  # fmt: skip
    assert style.labels(pct) == ["Ballbesitzteam", "Offensiv druckvoll", "Steriler Ballbesitz",
                                 "Schwache Chancenverwertung", "Defensiv kompakt"]  # fmt: skip
    assert style.labels(pd.Series(dtype=float)) == []
