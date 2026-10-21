"""Expected starting XI before the confirmed line-up is out (20–40 minutes before kickoff).

API-Football has no predicted line-ups, so we derive one from the team's recent line-ups (all
competitions, only matches before kickoff) and the reported absences (``core.injuries``: injured, suspended,
"Questionable"). Method (backtest: ``qf model lineup-eval`` → ``docs/21_aufstellung.md``): formation and
slots of the last match, absent players are replaced by the available player of the same position with the
most recent starts. Display only, the models do not use it.
"""

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text

RECENT_N = 5  # line-ups considered per team
DECAY = 0.6  # weight of a start i matches ago: DECAY ** i
QUESTIONABLE = "Questionable"
FINISHED = ("FT", "AET", "PEN")

HISTORY_SQL = """
    select p.fixture_id, f.kickoff_utc as kickoff, f.league_id, p.team_id, p.player_id, p.player_name,
           p.number, p.pos, p.grid, p.is_starter, p.sort, l.formation
    from core.fixture_lineup_players p
    join core.fixtures f on f.id = p.fixture_id
    left join core.fixture_lineups l on l.fixture_id = p.fixture_id and l.team_id = p.team_id
    where f.status in ('FT', 'AET', 'PEN') {where}
"""


def load_history(
    engine, team_ids: list[int] | None = None, before=None, per_team: int = RECENT_N
) -> pd.DataFrame:
    """Line-ups of finished matches; with ``team_ids`` / ``before`` only the last ``per_team`` per team."""
    where, params = "", {}
    if team_ids is not None:
        where = """and (p.fixture_id, p.team_id) in (
            select r.id, t.team_id from unnest(cast(:teams as int[])) as t(team_id)
            cross join lateral (
                select f2.id from core.fixtures f2
                where (f2.home_team_id = t.team_id or f2.away_team_id = t.team_id)
                  and f2.kickoff_utc < :before and f2.status in ('FT', 'AET', 'PEN')
                  and exists (select 1 from core.fixture_lineup_players x where x.fixture_id = f2.id
                              and x.team_id = t.team_id)
                order by f2.kickoff_utc desc limit :n
            ) r)"""
        params = {"teams": team_ids, "before": before, "n": per_team}
    with engine.connect() as conn:
        out = pd.read_sql(text(HISTORY_SQL.format(where=where)), conn, params=params)
    out["kickoff"] = pd.to_datetime(out["kickoff"], utc=True)
    return out


def load_absences(engine, fixture_ids: list[int]) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            text("""select i.fixture_id, i.team_id, i.player_id,
                           coalesce(i.player_name, pl.name) as player_name, i.type, i.reason
                    from core.injuries i left join core.players pl on pl.id = i.player_id
                    where i.fixture_id = any(:ids)"""),
            conn,
            params={"ids": fixture_ids},
        )


@dataclass
class Absences:
    missing: set[int]
    questionable: set[int]

    @classmethod
    def of(cls, rows: pd.DataFrame) -> "Absences":
        q = rows["type"] == QUESTIONABLE
        return cls(set(rows.loc[~q, "player_id"].astype(int)), set(rows.loc[q, "player_id"].astype(int)))


def _scores(recent: pd.DataFrame, order: list[int]) -> pd.Series:
    """Recency-weighted starts per player (bench appearances count a little, so squad players rank)."""
    weight = {fid: DECAY**i for i, fid in enumerate(order)}
    w = recent["fixture_id"].map(weight) * recent["is_starter"].map({True: 1.0, False: 0.15})
    return w.groupby(recent["player_id"]).sum()


def predict(history: pd.DataFrame, absences: Absences, adjust: bool = True, n: int = RECENT_N) -> dict | None:
    """Expected starting XI from the line-ups of one team (rows before kickoff only).

    Returns ``{"basis": {fixture_id, kickoff}, "formation", "start": [...]}``; each starter has
    ``replaces`` (name of the absent player whose slot he takes) and ``questionable``."""
    if history.empty:
        return None
    order = (history.drop_duplicates("fixture_id").sort_values("kickoff", ascending=False)["fixture_id"]
             .head(n).tolist())  # fmt: skip
    recent = history[history["fixture_id"].isin(order)]
    base = recent[(recent["fixture_id"] == order[0]) & recent["is_starter"]].sort_values("sort")
    scores = _scores(recent, order)
    latest = recent.sort_values("kickoff").drop_duplicates("player_id", keep="last").set_index("player_id")
    chosen = set(base["player_id"].astype(int))
    start = []
    for row in base.itertuples():
        pid, replaces = int(row.player_id), None
        if adjust and pid in absences.missing:
            pool = [p for p in scores.sort_values(ascending=False).index.astype(int)
                    if p not in chosen and p not in absences.missing]  # fmt: skip
            same = [p for p in pool if latest.at[p, "pos"] == row.pos]
            other = [p for p in pool if (latest.at[p, "pos"] == "G") == (row.pos == "G")]
            pick = (same or other or [None])[0]
            if pick is not None:
                replaces, pid = row.player_name, pick
                chosen.add(pick)
        info = latest.loc[pid] if pid in latest.index else row
        start.append(
            {"player_id": pid, "name": info.player_name, "number": _int(info.number), "pos": row.pos,
             "grid": row.grid, "replaces": replaces, "questionable": pid in absences.questionable,
             "absent": pid in absences.missing}
        )  # fmt: skip
    first = recent[recent["fixture_id"] == order[0]].iloc[0]
    return {
        "basis": {"fixture_id": int(order[0]), "kickoff": first["kickoff"].isoformat()},
        "formation": first["formation"],
        "start": start,
    }


def _int(v) -> int | None:
    return None if v is None or pd.isna(v) else int(v)


# --------------------------------------------------------------------------- backtest

VARIANTS = {"letzte Startelf": False, "letzte Startelf, Ausfälle ersetzt": True}


def load_eval_fixtures(engine, league_ids: list[int], seasons: list[int]) -> pd.DataFrame:
    with engine.connect() as conn:
        out = pd.read_sql(
            text("""select f.id as fixture_id, t.team_id, f.kickoff_utc as kickoff, f.league_id, f.season
                    from core.fixtures f
                    join lateral (values (f.home_team_id), (f.away_team_id)) t(team_id) on true
                    where f.league_id = any(:leagues) and f.season = any(:seasons)
                      and f.status in ('FT', 'AET', 'PEN')"""),
            conn,
            params={"leagues": league_ids, "seasons": seasons},
        )
    out["kickoff"] = pd.to_datetime(out["kickoff"], utc=True)
    return out


def evaluate(history: pd.DataFrame, absences: pd.DataFrame, fixtures: pd.DataFrame) -> pd.DataFrame:
    """Expected vs. confirmed starting XI for ``fixtures`` (fixture_id, team_id, kickoff, league_id, season).

    Uses only line-ups of matches before kickoff. One row per team and match: correct starters per variant
    and whether the goalkeeper was right."""
    by_team = {t: g.sort_values("kickoff") for t, g in history.groupby("team_id")}
    by_fixture = {k: g for k, g in absences.groupby(["fixture_id", "team_id"])}
    empty = absences.iloc[0:0]
    rows = []
    for f in fixtures.itertuples():
        team = by_team.get(f.team_id)
        if team is None:
            continue
        actual = team[(team["fixture_id"] == f.fixture_id) & team["is_starter"]]
        before = team[team["kickoff"] < f.kickoff]
        if len(actual) != 11 or before.empty:
            continue
        ab = Absences.of(by_fixture.get((f.fixture_id, f.team_id), empty))
        truth = set(actual["player_id"].astype(int))
        keeper = set(actual.loc[actual["pos"] == "G", "player_id"].astype(int))
        row = {"league_id": f.league_id, "season": f.season, "absent": len(ab.missing)}
        for name, adjust in VARIANTS.items():
            pred = predict(before, ab, adjust=adjust)
            start = pred["start"] if pred else []
            row[name] = len(truth & {p["player_id"] for p in start})
            row[f"{name}|keeper"] = any(p["player_id"] in keeper for p in start if p["pos"] == "G")
        rows.append(row)
    return pd.DataFrame(rows)


def report(result: pd.DataFrame, league_names: dict[int, str], seasons: list[int]) -> str:
    from datetime import UTC, datetime

    f = lambda x, d=2: f"{x:.{d}f}".replace(".", ",")  # noqa: E731
    pct = lambda x: f"{x * 100:.0f} %"  # noqa: E731
    out = [
        "# 21 – Voraussichtliche Aufstellung",
        "",
        f"Automatisch erzeugt von `qf model lineup-eval` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC. Ligen: "
        f"{', '.join(league_names.values())}, Saisons {seasons[0]}/{(seasons[0] + 1) % 100:02d}–"
        f"{seasons[-1]}/{(seasons[-1] + 1) % 100:02d}, {len(result)} Startelfen.",
        "",
        "**Idee:** API-Football liefert keine voraussichtlichen Aufstellungen, die bestätigte kommt erst "
        "20–40 Minuten vor Anpfiff. Bis dahin zeigt die Detailseite eine eigene Schätzung: die Startelf des "
        "letzten Spiels (alle Wettbewerbe, Formation und Positionen übernommen); gemeldete Ausfälle "
        "(verletzt, gesperrt) werden durch den verfügbaren Spieler derselben Position mit den meisten "
        f"Einsätzen in den letzten {RECENT_N} Spielen ersetzt. Gemessen wird, wie viele der 11 geschätzten "
        "Spieler tatsächlich begonnen haben.",
        "",
        "| Variante | Startelfen | richtig im Schnitt | mind. 10 richtig | alle 11 richtig "
        "| Torwart richtig |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in VARIANTS:
        h = result[name]
        out.append(f"| {name} | {len(h)} | {f(h.mean())} von 11 | {pct((h >= 10).mean())} | "
                   f"{pct((h == 11).mean())} | {pct(result[f'{name}|keeper'].mean())} |")  # fmt: skip
    best = list(VARIANTS)[-1]
    with_absent = result[result["absent"] > 0]
    out += ["", "## Je Liga und Saison (Variante mit ersetzten Ausfällen)", "",
            "| Liga | Saison | Startelfen | richtig im Schnitt | mind. 10 richtig |",
            "|---|---|---:|---:|---:|"]  # fmt: skip
    for (lg, season), g in result.groupby(["league_id", "season"]):
        out.append(f"| {league_names.get(lg, lg)} | {season}/{(season + 1) % 100:02d} | {len(g)} | "
                   f"{f(g[best].mean())} | {pct((g[best] >= 10).mean())} |")  # fmt: skip
    out += [
        "",
        "## Bewertung",
        "",
        f"- Mit gemeldeten Ausfällen ({len(with_absent)} Startelfen) bringt das Ersetzen "
        f"{f(with_absent[best].mean() - with_absent[list(VARIANTS)[0]].mean())} richtige Spieler mehr.",
        "- Die Schätzung ist eine Orientierung bis zur offiziellen Aufstellung, kein Modell-Input: Prognosen "
        "und Torschützen-Wahrscheinlichkeiten verwenden sie nicht.",
        "- Einschränkung: Die Ausfall-Liste der API wird bis kurz vor Anpfiff ergänzt; im Backtest steht der "
        "letzte Stand, live kann er unvollständiger sein (Abruf täglich).",
        "",
    ]
    return "\n".join(out)
