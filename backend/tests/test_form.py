"""Form pattern: points above/below the model's expectation over the last matches (no database)."""

import pandas as pd
import pytest

from quotenfabrik.analytics import form


def history() -> pd.DataFrame:
    rows = []
    kickoff = pd.Timestamp("2026-08-01", tz="UTC")
    for i in range(8):  # team 1 always at home against team 2+i, wins the first six, then loses
        hg, ag = (2, 0) if i < 6 else (0, 1)
        p = (None, None, None) if i == 0 else (0.5, 0.25, 0.25)  # first match without prediction
        rows.append((i + 1, kickoff + pd.Timedelta(days=7 * i), 78, "Bundesliga", "Regular Season - 1", 1, 2 + i,
                     hg, ag, *p))  # fmt: skip
    return pd.DataFrame(rows, columns=["fixture_id", "kickoff", "league_id", "league_name", "round", "home_id",
                                       "away_id", "hg", "ag", "p_h", "p_d", "p_a"])  # fmt: skip


def test_team_rows_points_and_expectation():
    rows = form.team_rows(history())
    home = rows[rows["team"] == 1]
    assert list(home["points"])[:2] == [3, 3]
    assert home["xpts"].iloc[0] != home["xpts"].iloc[0]  # NaN without prediction
    assert home["xpts"].iloc[1] == pytest.approx(3 * 0.5 + 0.25)
    away = rows[rows["fixture_id"] == 2].set_index("venue")
    assert away.loc["away", "points"] == 0 and away.loc["away", "xpts"] == pytest.approx(3 * 0.25 + 0.25)


def test_team_form_last_six():
    rows = form.team_rows(history())
    f = form.team_form(rows[rows["team"] == 1])
    assert f.matches == 6 and f.sequence == "SSSSNN"
    assert f.ppg == pytest.approx(2.0)
    assert f.residual == pytest.approx((4 * 3 + 2 * 0) / 6 - 1.75)
    assert f.n_expected == 6 and f.signal is None


def test_team_form_needs_enough_predicted_matches():
    rows = form.team_rows(history().head(4))  # 3 matches with prediction
    f = form.team_form(rows[rows["team"] == 1])
    assert f.residual is None and f.signal is None and f.sequence == "SSSS"


def test_rolling_form_uses_only_earlier_matches():
    rows = form.rolling_form(form.team_rows(history()))
    team = rows[rows["team"] == 1].set_index("fixture_id")
    # before match 6: matches 2-5 have predictions (4) -> residual of four wins: 3 - 1.75
    assert team.loc[6, "form_residual"] == pytest.approx(1.25)
    # match 7 is the first loss; its own result must not enter its form value
    assert team.loc[7, "form_residual"] == pytest.approx(1.25)
    assert pd.isna(team.loc[5, "form_residual"])  # only 3 predicted matches before match 5
