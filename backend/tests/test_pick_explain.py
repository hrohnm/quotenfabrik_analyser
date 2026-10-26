import math

from quotenfabrik.analytics.pick_explain import FixtureContext, explain, team_goals

CTX = FixtureContext("Bayern", "Leipzig", 0.69, 0.17, 0.14, 2.8, 1.2)


def _pick(**kw):
    return {"rank": 1, "group": "totals", "market": "ou_ft", "selection": "over", "line": 1.5, "probability": 0.77,
            "base_rate": 0.51, "reasons": [], "betano": None, "edge": None, "pinnacle": None, **kw}  # fmt: skip


def _explain(pick, track=None):
    return explain(pick, profile_label="Ausgewogen", min_p=0.58, max_p=0.85, group_label="Tore gesamt", n_picks=3,
                   ctx=CTX, track=track)  # fmt: skip


def test_team_goals_inverts_poisson_zero():
    assert math.isclose(team_goals(1 - math.exp(-1.4)), 1.4)
    assert team_goals(None) is None and team_goals(1.0) is None


def test_goal_pick_explains_profile_lift_and_expected_goals():
    out = _explain(_pick(reasons=[{"label": "Heimteam 2+ Tore", "value": 0.9, "baseline": 0.51}]))
    assert "58–85" in out["why"][0] and "Tore gesamt" in out["why"][1]
    assert "Deutlich über dem Ligaschnitt" in out["why"][2] and "+26 Punkte" in out["why"][2]
    assert out["likely"][0].startswith("Das Modell erwartet 4,0 Tore (Bayern 2,8, Leipzig 1,2)")
    assert any(line.startswith("Pattern: Heimteam 2+ Tore: 90") for line in out["likely"])


def test_result_pick_uses_1x2_market_prices_and_track_record():
    pick = _pick(group="1x2", market="1x2", selection="H", line=None, probability=0.69, base_rate=0.44,
                 betano=1.23, edge=0.69 * 1.23 - 1, pinnacle=0.70)  # fmt: skip
    out = _explain(pick, track={"n": 1615, "hit_rate": 0.79, "expected": 0.78})
    text = " ".join(out["likely"])
    assert "Sieg Bayern 69" in text and "bestätigt das Modell" in text and "Betano-Quote 1,23" in text
    assert "1.615 abgerechnet" in text
    assert "abgerechnet" not in " ".join(
        _explain(pick, track={"n": 5, "hit_rate": 1, "expected": 0.7})["likely"]
    )


def test_pick_near_or_below_base_rate():
    assert "Etwa im Ligaschnitt" in _explain(_pick(probability=0.52))["why"][2]
    assert "Unter dem Ligaschnitt" in _explain(_pick(probability=0.40))["why"][2]
    assert len(_explain(_pick(base_rate=None))["why"]) == 2
