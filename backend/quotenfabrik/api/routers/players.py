"""Player page: header (team, number, status, next match with scorer forecast), season values, matches with
scorer forecasts, absences."""

import pandas as pd
from fastapi import APIRouter, HTTPException

from quotenfabrik import app_config
from quotenfabrik.analytics import player_stats
from quotenfabrik.analytics.availability import absence_reason
from quotenfabrik.api.data import chosen_runs_cte, df
from quotenfabrik.api.labels import MEDIA_BASE, league_logo

router = APIRouter(prefix="/api", tags=["players"])

FINISHED = ("FT", "AET", "PEN", "AWD", "WO")


def _clean(v):
    if v is None or (isinstance(v, float) and v != v):
        return None
    return v.item() if hasattr(v, "item") else v


def _rows(player_id: int) -> pd.DataFrame:
    """All match rows of the player (competitions with player data), with fixture and result."""
    rows = df(
        """select s.fixture_id, s.team_id, s.is_starter, s.minutes, s.goals, s.assists, s.shots_total, s.shots_on,
                  s.key_passes, s.yellow, s.red, s.penalties_scored, s.penalties_missed, s.rating::float as rating,
                  s.position, f.league_id, f.season, f.kickoff_utc as kickoff, f.home_team_id, f.away_team_id,
                  f.ft_home, f.ft_away, f.status
           from core.fixture_player_stats s join core.fixtures f on f.id = s.fixture_id
           where s.player_id = :p order by f.kickoff_utc""",
        p=player_id,
    )  # fmt: skip
    rows["kickoff"] = pd.to_datetime(rows["kickoff"], utc=True)
    return rows


def _teams(ids) -> dict[int, dict]:
    t = df(
        "select id, name, logo_url from core.teams where id = any(:ids)", ids=sorted({int(i) for i in ids})
    )
    return {int(r.id): {"id": int(r.id), "name": r.name, "logo": r.logo_url} for r in t.itertuples()}


def _leagues(ids) -> dict[int, dict]:
    t = df("select id, name from core.leagues where id = any(:ids)", ids=sorted({int(i) for i in ids}))
    return {
        int(r.id): {"id": int(r.id), "name": r.name, "logo": league_logo(int(r.id))} for r in t.itertuples()
    }


def _scorer_probabilities(player_id: int, fixture_ids: list[int]) -> pd.DataFrame:
    if not fixture_ids:
        return pd.DataFrame(columns=["fixture_id", "p_anytime", "p_first"])
    p = df(
        f"""with runs as ({chosen_runs_cte("and p.fixture_id = any(:ids)")})
            select p.fixture_id, p.market, p.probability from analytics.predictions p
            join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            where p.fixture_id = any(:ids) and p.market in ('scorer_anytime', 'scorer_first') and p.selection = :sel""",
        ids=fixture_ids, sel=str(player_id),
    )  # fmt: skip
    if p.empty:
        return pd.DataFrame(columns=["fixture_id", "p_anytime", "p_first"])
    wide = p.pivot_table(index="fixture_id", columns="market", values="probability").reset_index()
    return wide.rename(columns={"scorer_anytime": "p_anytime", "scorer_first": "p_first"})


@router.get("/players/{player_id}")
def player_overview(player_id: int, season: int | None = None) -> dict:
    """Header and overview: team, number, position, status, next match with scorer forecast, season values
    (total, per competition, per 90 minutes, share in the team), penalties, seasons."""
    player = df("select id, name from core.players where id = :id", id=player_id)
    if player.empty:
        raise HTTPException(404, "Spieler nicht gefunden")
    rows = _rows(player_id)
    if rows.empty:
        raise HTTPException(404, "Keine Spielerdaten")
    seasons = sorted({int(s) for s in rows["season"]}, reverse=True)
    season = season if season in seasons else seasons[0]
    current = rows[rows["season"] == season]
    team_id = int(rows["team_id"].iloc[-1])
    lineup = df(
        """select lp.number, lp.pos from core.fixture_lineup_players lp join core.fixtures f on f.id = lp.fixture_id
           where lp.player_id = :p order by f.kickoff_utc desc limit 1""",
        p=player_id,
    )  # fmt: skip
    next_fixture = df(
        """select f.id, f.kickoff_utc, f.league_id, f.home_team_id, f.away_team_id from core.fixtures f
           where (f.home_team_id = :t or f.away_team_id = :t) and f.kickoff_utc > now() - interval '2 hours'
             and f.status not in ('FT', 'AET', 'PEN', 'PST', 'CANC', 'ABD') and f.league_id = any(:leagues)
           order by f.kickoff_utc limit 1""",
        t=team_id, leagues=app_config.shown_league_ids(),
    )  # fmt: skip
    status, upcoming = None, None
    if not next_fixture.empty:
        nf = next_fixture.iloc[0]
        absent = df("select type, reason from core.injuries where fixture_id = :f and player_id = :p",
                    f=int(nf.id), p=player_id)  # fmt: skip
        if not absent.empty:
            status = {"type": "doubtful" if absent.type[0] == "Questionable" else "missing",
                      "reason": absence_reason(_clean(absent.reason[0]))}  # fmt: skip
        probs = _scorer_probabilities(player_id, [int(nf.id)])
        home = int(nf.home_team_id) == team_id
        upcoming = {
            "fixture_id": int(nf.id), "kickoff": pd.Timestamp(nf.kickoff_utc).isoformat(),
            "league_id": int(nf.league_id), "home": home,
            "opponent_id": int(nf.away_team_id if home else nf.home_team_id),
            "p_anytime": None if probs.empty else _clean(probs["p_anytime"].iloc[0]),
            "p_first": None if probs.empty or "p_first" not in probs else _clean(probs["p_first"].iloc[0]),
        }  # fmt: skip

    summary = player_stats.summary(current)
    played_ids = current.loc[(current["minutes"].fillna(0) > 0), "fixture_id"].astype(int).tolist()
    team_totals = {"matches": len(played_ids)}
    if played_ids:
        t = df(
            """select sum(case when f.home_team_id = :t then f.ft_home else f.ft_away end) as goals,
                      (select sum(coalesce(s.assists, 0)) from core.fixture_player_stats s
                       where s.team_id = :t and s.fixture_id = any(:ids)) as assists,
                      (select sum(ts.shots_total) from core.fixture_team_stats ts
                       where ts.team_id = :t and ts.period = 'FT' and ts.fixture_id = any(:ids)) as shots
               from core.fixtures f where f.id = any(:ids)""",
            t=team_id, ids=played_ids,
        ).iloc[0]  # fmt: skip
        team_totals |= {k: float(t[k] or 0) for k in ("goals", "assists", "shots")}
    competitions = player_stats.by_competition(current)
    career = []
    for s, g in rows.groupby("season"):
        sm = player_stats.summary(g)
        if sm["apps"]:
            career.append({"season": int(s), "team_id": int(g["team_id"].iloc[-1]),
                           **{k: sm[k] for k in ("apps", "minutes", "goals", "assists", "rating")}})  # fmt: skip
    pens = rows[["penalties_scored", "penalties_missed"]].fillna(0).sum()
    recent = rows[rows["kickoff"] > pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=365)]
    team_ids = {team_id} | {c["team_id"] for c in career}
    if upcoming:
        team_ids.add(upcoming["opponent_id"])
    league_ids = {c["league_id"] for c in competitions} | ({upcoming["league_id"]} if upcoming else set())
    position = rows["position"].dropna()
    return {
        "player": {"id": player_id, "name": player.name[0], "photo": f"{MEDIA_BASE}/players/{player_id}.png"},
        "team_id": team_id,
        "number": None if lineup.empty else _clean(lineup.number[0]),
        "position": position.iloc[-1] if len(position) else (None if lineup.empty else _clean(lineup.pos[0])),
        "status": status,
        "next": upcoming,
        "season": season,
        "seasons": seasons,
        "summary": summary,
        "team_share": player_stats.team_share(summary, team_totals) if summary["apps"] else None,
        "competitions": competitions,
        "career": sorted(career, key=lambda c: -c["season"]),
        "penalties": {"scored": int(pens["penalties_scored"]), "missed": int(pens["penalties_missed"]),
                      "taker": bool(recent[["penalties_scored", "penalties_missed"]].fillna(0).to_numpy().sum() > 0)},
        "teams": _teams(team_ids),
        "leagues": _leagues(league_ids),
    }  # fmt: skip


@router.get("/players/{player_id}/matches")
def player_matches(player_id: int, season: int) -> dict:
    """Matches of the season with the player's values and the scorer forecast before the match."""
    rows = _rows(player_id)
    rows = rows[rows["season"] == season]
    if rows.empty:
        return {"season": season, "matches": [], "scoring": None, "teams": {}, "leagues": {}}
    probs = _scorer_probabilities(player_id, rows["fixture_id"].astype(int).tolist())
    rows = rows.merge(probs, on="fixture_id", how="left")
    matches = []
    for r in rows.sort_values("kickoff", ascending=False).itertuples():
        home = int(r.home_team_id) == int(r.team_id)
        finished = r.status in FINISHED and pd.notna(r.ft_home)
        score = [int(r.ft_home), int(r.ft_away)] if finished else None
        if score and not home:
            score = score[::-1]
        matches.append({
            "fixture_id": int(r.fixture_id), "kickoff": r.kickoff.isoformat(), "league_id": int(r.league_id),
            "home": home, "opponent_id": int(r.away_team_id if home else r.home_team_id), "score": score,
            "starter": bool(r.is_starter) if pd.notna(r.is_starter) else None, "minutes": _clean(r.minutes),
            "goals": _clean(r.goals), "assists": _clean(r.assists), "shots": _clean(r.shots_total),
            "shots_on": _clean(r.shots_on), "yellow": _clean(r.yellow), "red": _clean(r.red),
            "rating": _clean(r.rating), "p_anytime": _clean(getattr(r, "p_anytime", None)),
            "p_first": _clean(getattr(r, "p_first", None)),
        })  # fmt: skip
    played = rows[rows["minutes"].fillna(0) > 0]
    return {
        "season": season,
        "matches": matches,
        "scoring": player_stats.scoring_track(played) if "p_anytime" in played else None,
        "teams": _teams(set(rows["home_team_id"]) | set(rows["away_team_id"])),
        "leagues": _leagues(set(rows["league_id"])),
    }


@router.get("/players/{player_id}/absences")
def player_absences(player_id: int) -> dict:
    """Reported absences of the player (all seasons, from 2021 on)."""
    a = df(
        """select i.fixture_id, i.team_id, i.type, i.reason, f.kickoff_utc as kickoff, f.league_id,
                  f.home_team_id, f.away_team_id
           from core.injuries i join core.fixtures f on f.id = i.fixture_id
           where i.player_id = :p order by f.kickoff_utc desc""",
        p=player_id,
    )  # fmt: skip
    if a.empty:
        return {
            "absences": [],
            "summary": {"missed": 0, "doubtful": 0, "reasons": []},
            "teams": {},
            "leagues": {},
        }
    a["reason_label"] = a["reason"].map(absence_reason)
    items = [{"fixture_id": int(r.fixture_id), "kickoff": pd.Timestamp(r.kickoff).isoformat(),
              "league_id": int(r.league_id), "type": "doubtful" if r.type == "Questionable" else "missing",
              "reason": r.reason_label,
              "opponent_id": int(r.away_team_id if int(r.home_team_id) == int(r.team_id) else r.home_team_id)}
             for r in a.itertuples()]  # fmt: skip
    return {
        "absences": items,
        "summary": player_stats.absence_summary(a),
        "teams": _teams({i["opponent_id"] for i in items}),
        "leagues": _leagues({i["league_id"] for i in items}),
    }
