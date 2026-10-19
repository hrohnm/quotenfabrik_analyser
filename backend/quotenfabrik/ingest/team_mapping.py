"""Maps football-data.co.uk team names to API-Football team ids and links historical rows to fixtures.

football-data has no ids. A row is matched to an API fixture with the same date (+/- 1 day) and identical
full-time and half-time score. Unique matches vote for alias -> team id; the majority wins.
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from quotenfabrik.ingest.db_utils import upsert
from quotenfabrik.models import Fixture, HistoricalMatch, TeamAlias

log = logging.getLogger(__name__)

SOURCE = "football_data"
LOCAL_TZ = ZoneInfo("Europe/Berlin")
MIN_VOTES = 2
MIN_SHARE = 0.7


@dataclass
class MappingReport:
    aliases_total: int = 0
    aliases_new: int = 0
    rows_linked: int = 0
    rows_unlinked: int = 0
    unmapped_aliases: list[str] = field(default_factory=list)
    unlinked_examples: list[str] = field(default_factory=list)


def _score_key(d: date, ft_h, ft_a, ht_h, ht_a) -> tuple:
    return (d, ft_h, ft_a, ht_h, ht_a)


def map_and_link(session: Session, league_id: int, league_code: str) -> MappingReport:
    report = MappingReport()
    fixtures = session.execute(
        select(
            Fixture.id, Fixture.kickoff_utc, Fixture.home_team_id, Fixture.away_team_id,
            Fixture.ft_home, Fixture.ft_away, Fixture.ht_home, Fixture.ht_away,
        ).where(Fixture.league_id == league_id, Fixture.ft_home.is_not(None))
    ).all()  # fmt: skip
    by_score: dict[tuple, list] = defaultdict(list)
    by_teams: dict[tuple[int, int], list] = defaultdict(list)
    for f in fixtures:
        local_day = f.kickoff_utc.astimezone(LOCAL_TZ).date()
        by_score[_score_key(local_day, f.ft_home, f.ft_away, f.ht_home, f.ht_away)].append(f)
        by_teams[(f.home_team_id, f.away_team_id)].append((local_day, f.id))

    rows = session.scalars(select(HistoricalMatch).where(HistoricalMatch.league_code == league_code)).all()

    # 1) votes from rows with exactly one candidate fixture
    votes: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        candidates = [
            f
            for delta in (-1, 0, 1)
            for f in by_score.get(
                _score_key(
                    row.match_date + timedelta(days=delta), row.ft_home, row.ft_away, row.ht_home, row.ht_away
                ),
                [],
            )
        ]
        if len(candidates) == 1:
            votes[row.home_alias][candidates[0].home_team_id] += 1
            votes[row.away_alias][candidates[0].away_team_id] += 1

    existing = {
        a.alias: a.team_id for a in session.scalars(select(TeamAlias).where(TeamAlias.source == SOURCE))
    }
    new_aliases = []
    for alias, counter in votes.items():
        team_id, count = counter.most_common(1)[0]
        if alias in existing:
            if existing[alias] != team_id:
                log.warning("Alias %r is mapped to %s, votes suggest %s", alias, existing[alias], team_id)
            continue
        if count >= MIN_VOTES and count / sum(counter.values()) >= MIN_SHARE:
            new_aliases.append({"source": SOURCE, "alias": alias, "team_id": team_id, "matched_games": count})
            existing[alias] = team_id
    upsert(session, TeamAlias, new_aliases)
    report.aliases_new = len(new_aliases)
    report.aliases_total = len(existing)
    report.unmapped_aliases = sorted(
        ({r.home_alias for r in rows} | {r.away_alias for r in rows}) - set(existing)
    )

    # 2) link rows via (home id, away id, date +/- 1 day)
    for row in rows:
        home, away = existing.get(row.home_alias), existing.get(row.away_alias)
        match = None
        if home and away:
            match = next(
                (fid for day, fid in by_teams.get((home, away), []) if abs((day - row.match_date).days) <= 1),
                None,
            )
        if match:
            if row.fixture_id != match:
                session.execute(
                    update(HistoricalMatch).where(HistoricalMatch.id == row.id).values(fixture_id=match)
                )
            report.rows_linked += 1
        else:
            report.rows_unlinked += 1
            if len(report.unlinked_examples) < 20:
                report.unlinked_examples.append(f"{row.match_date} {row.home_alias} - {row.away_alias}")
    session.commit()
    return report
