"""Paths of the generated Markdown reports (docs/09 – docs/12), one file per league."""

import re
from pathlib import Path

from quotenfabrik import app_config

DOCS = Path(__file__).resolve().parents[2] / "docs"
EVALUATION_REPORT = DOCS / "09_modell_evaluation.md"
ODDS_REPORT = DOCS / "10_quoten_backtest.md"
BETANO_REPORT = DOCS / "11_betano_nebenmaerkte.md"
PICKS_REPORT = DOCS / "12_tipps.md"
JOINT_REPORT = DOCS / "14_gemeinsames_modell.md"
CUP_REPORT = DOCS / "15_europapokal.md"
COMBO_REPORT = DOCS / "16_tageskombis.md"
FORM_REPORT = DOCS / "17_form.md"
STYLE_REPORT = DOCS / "18_spielstil.md"
SHOTS_REPORT = DOCS / "19_schuesse_im_modell.md"
LINEUP_REPORT = DOCS / "21_aufstellung.md"
CALIBRATION_REPORT = DOCS / "20_kalibrierung.md"


def report_path(path: Path | None, league_id: int) -> Path | None:
    """The first configured league writes ``path``; other leagues get a suffix (``…_2_bundesliga.md``)."""
    if path is None or league_id == app_config.all_leagues()[0].id:
        return path
    from quotenfabrik.analytics.data import league_name
    from quotenfabrik.db import get_engine

    name = league_name(get_engine(), league_id)
    lg = app_config.league(league_id)
    if any(o.name == name and o.id != league_id for o in app_config.all_leagues()) and lg.country:
        name = f"{lg.country} {name}"  # e.g. Austrian "Bundesliga" next to the German one
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return path.with_name(f"{path.stem}_{slug}{path.suffix}")
