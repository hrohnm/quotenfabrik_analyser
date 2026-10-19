from datetime import date, time
from decimal import Decimal

from quotenfabrik.sources import football_data
from tests.conftest import DATA


def test_season_code_and_url():
    assert football_data.season_code(2025) == "2526"
    assert football_data.season_code(2099) == "9900"
    assert football_data.season_url(2015, "D1").endswith("/1516/D1.csv")


def test_parse_current_format():
    rows = football_data.parse((DATA / "D1_2526_sample.csv").read_bytes(), "D1", "2526")
    assert len(rows) == 5
    first = rows[0].values
    assert first["match_date"] == date(2025, 8, 22)
    assert first["kickoff_local"] == time(19, 30)
    assert (first["home_alias"], first["away_alias"]) == ("Bayern Munich", "RB Leipzig")
    assert (first["ft_home"], first["ft_away"], first["ht_home"], first["ht_away"]) == (6, 0, 3, 0)
    assert first["b365_h"] == Decimal("1.22")
    assert first["psc_h"] is not None and first["avgc_o25"] is not None
    assert rows[0].raw["Div"] == "D1"  # BOM stripped from first header


def test_parse_old_format_uses_fallback_columns():
    rows = football_data.parse((DATA / "D1_1516_sample.csv").read_bytes(), "D1", "1516")
    assert rows
    v = rows[0].values
    assert v["kickoff_local"] is None
    assert v["avg_h"] is not None  # from BbAvH
    assert v["avg_o25"] is not None  # from BbAv>2.5
    assert v["hxg"] is None
