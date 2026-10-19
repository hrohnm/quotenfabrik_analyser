from fastapi import APIRouter

from quotenfabrik.api.data import df, records
from quotenfabrik.api.labels import GROUP_LABELS, MARKET_LABELS, SELECTION_LABELS, league_logo
from quotenfabrik.config import get_settings

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta")
def meta() -> dict:
    leagues = df(
        "select id, name, country from core.leagues where id = any(:ids) order by id",
        ids=get_settings().leagues,
    )
    seasons = df(
        "select distinct season from core.fixtures where league_id = any(:ids) order by season desc",
        ids=get_settings().leagues,
    )
    teams = df(
        """select distinct t.id, t.name, t.logo_url from core.teams t
           join core.fixtures f on t.id in (f.home_team_id, f.away_team_id)
           where f.league_id = any(:ids) order by t.name""",
        ids=get_settings().leagues,
    )
    markets = df(
        """select p.market_group, p.market, p.line, array_agg(distinct p.selection) as selections
           from analytics.predictions p join analytics.model_runs r on r.id = p.model_run_id
           where r.kind = 'backtest' and p.market not like 'scorer%'
           group by 1, 2, 3 order by 1, 2, 3"""
    )
    runs = df(
        """select id, kind, model_version, as_of, created_at, summary from analytics.model_runs
           where kind in ('forecast', 'backtest') order by id desc limit 5"""
    )
    return {
        "leagues": [{**lg, "logo": league_logo(lg["id"])} for lg in records(leagues)],
        "seasons": [int(s) for s in seasons["season"]],
        "teams": records(teams),
        "groups": GROUP_LABELS,
        "market_labels": MARKET_LABELS,
        "selection_labels": SELECTION_LABELS,
        "markets": [
            {
                "group": r.market_group,
                "market": r.market,
                "line": None if r.line is None else float(r.line),
                "selections": sorted(r.selections),
            }
            for r in markets.itertuples()
        ],  # fmt: skip
        "runs": records(runs),
    }
