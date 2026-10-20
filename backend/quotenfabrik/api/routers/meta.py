from fastapi import APIRouter

from quotenfabrik import app_config
from quotenfabrik.analytics.picks import default_profile, profiles
from quotenfabrik.api.data import df, records
from quotenfabrik.api.labels import GROUP_LABELS, MARKET_LABELS, SELECTION_LABELS, league_logo

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta")
def meta() -> dict:
    leagues = df(
        "select id, name, country from core.leagues where id = any(:ids) order by id",
        ids=app_config.shown_league_ids(),
    )
    seasons = df(
        "select distinct season from core.fixtures where league_id = any(:ids) order by season desc",
        ids=app_config.shown_league_ids(),
    )
    teams = df(
        """select distinct t.id, t.name, t.logo_url from core.teams t
           join core.fixtures f on t.id in (f.home_team_id, f.away_team_id)
           where f.league_id = any(:ids) order by t.name""",
        ids=app_config.shown_league_ids(),
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
        "leagues": _league_list(records(leagues)),
        "seasons": [int(s) for s in seasons["season"]],
        "teams": records(teams),
        "groups": GROUP_LABELS,
        "pick_profiles": [
            {
                "key": k,
                "label": p.label,
                "min_p": p.min_p,
                "max_p": p.max_p,
                "default": k == default_profile(),
            }
            for k, p in profiles().items()
        ],
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


def _league_list(rows: list[dict]) -> list[dict]:
    """Configured order; leagues with the same name get their country (e.g. two "Bundesliga")."""
    order = {lid: i for i, lid in enumerate(app_config.shown_league_ids())}
    names = [r["name"] for r in rows]
    out = []
    for r in sorted(rows, key=lambda r: order.get(r["id"], 99)):
        name = (
            f"{r['name']} ({r['country']})" if names.count(r["name"]) > 1 and r.get("country") else r["name"]
        )
        cup = app_config.is_cup(r["id"])
        name = name.removeprefix("UEFA ") if cup else name
        out.append({**r, "name": name, "logo": league_logo(r["id"]), "cup": cup})
    return out
