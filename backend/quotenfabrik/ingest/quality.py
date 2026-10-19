"""Data quality report per league season."""

from sqlalchemy import text
from sqlalchemy.orm import Session

_SQL = text(
    """
    with f as (
        select f.season, f.id, f.status, f.ft_home, f.ft_away, f.details_synced_at, f.half_stats_synced_at
        from core.fixtures f where f.league_id = :league
    ),
    goals as (
        -- regular time only (minute <= 90 incl. stoppage time), as betting markets settle after 90 minutes
        select e.fixture_id,
               count(*) filter (
                   where e.type = 'Goal' and e.detail <> 'Missed Penalty' and e.minute <= 90
               ) as n
        from core.fixture_events e join f on f.id = e.fixture_id group by e.fixture_id
    ),
    xg as (
        select distinct s.fixture_id from core.fixture_team_stats s join f on f.id = s.fixture_id
        where s.period = 'FT' and s.xg is not null
    ),
    hist as (
        select h.fixture_id from core.historical_matches h where h.fixture_id is not null
    )
    select f.season,
           count(*) as fixtures,
           count(*) filter (where f.status in ('FT','AET','PEN','AWD','WO')) as finished,
           count(f.details_synced_at) as with_details,
           count(f.half_stats_synced_at) as with_half_stats,
           count(xg.fixture_id) as with_xg,
           count(hist.fixture_id) as linked_football_data,
           count(*) filter (
               where goals.n is not null and goals.n <> f.ft_home + f.ft_away
           ) as goal_event_mismatch
    from f
    left join goals on goals.fixture_id = f.id
    left join xg on xg.fixture_id = f.id
    left join hist on hist.fixture_id = f.id
    group by f.season order by f.season
    """
)

COLUMNS = (
    "season", "fixtures", "finished", "with_details", "with_half_stats", "with_xg",
    "linked_football_data", "goal_event_mismatch",
)  # fmt: skip


def season_report(session: Session, league_id: int) -> list[dict]:
    return [dict(zip(COLUMNS, row, strict=True)) for row in session.execute(_SQL, {"league": league_id})]
