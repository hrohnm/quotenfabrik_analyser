"""Runtime configuration from the database (configuration page), with the environment as fallback.

- Leagues: ``app.leagues`` (active rows). Empty or missing table -> ``QF_LEAGUES`` / ``QF_FD_LEAGUES`` /
  ``QF_ODDSPAPI_TOURNAMENTS``.
- Settings: ``app.settings`` overrides the defaults of ``SETTINGS`` (thresholds, model parameters, reserves).
  Secrets (API keys, database URL) stay in the environment and are never stored here.
"""

import json
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from quotenfabrik.config import Settings, get_settings
from quotenfabrik.db import get_engine

CACHE_TTL_S = 15.0


@dataclass(frozen=True)
class SettingDef:
    key: str
    group: str
    label: str
    help: str
    type: str  # 'float', 'int' or 'choice'
    default: Any
    min: float | None = None
    max: float | None = None
    choices: tuple[str, ...] = ()
    percent: bool = False  # shown as percent in the UI (value stays 0-1)


def _profile(key: str, label: str, min_p: float, max_p: float, weight: float) -> list[SettingDef]:
    group = f"Tipps – Profil {label}"
    return [
        SettingDef(f"picks.{key}.min_p", group, "Wahrscheinlichkeit ab", "Untere Grenze je Tipp.", "float", min_p,
                   0.3, 0.99, percent=True),
        SettingDef(f"picks.{key}.max_p", group, "Wahrscheinlichkeit bis", "Obere Grenze je Tipp (sehr sichere Tipps "
                   "haben kaum Quote).", "float", max_p, 0.31, 1.0, percent=True),
        SettingDef(f"picks.{key}.lift_weight", group, "Gewicht Abstand zum Ligaschnitt", "0 = nur Wahrscheinlichkeit; "
                   "höher = Tipps bevorzugen, bei denen das Modell vom Ligaschnitt abweicht.", "float", weight, 0, 5),
    ]  # fmt: skip


PROFILE_KEYS = {"sicher": "Sicher", "ausgewogen": "Ausgewogen", "mutig": "Mutig"}

SETTINGS: list[SettingDef] = [
    *_profile("sicher", "Sicher", 0.70, 0.92, 0.5),
    *_profile("ausgewogen", "Ausgewogen", 0.58, 0.85, 1.0),
    *_profile("mutig", "Mutig", 0.45, 0.72, 1.0),
    SettingDef("picks.default_profile", "Tipps – Allgemein", "Standardprofil", "Profil auf Spieltagsübersicht und "
               "Tipps-Seite.", "choice", "ausgewogen", choices=tuple(PROFILE_KEYS)),
    SettingDef("model.xi", "Modell (wirkt nach „Modelle neu berechnen“)", "Zeitgewichtung ξ pro Tag",
               "Höher = jüngere Spiele zählen mehr (0,0015 ≈ Halbwertszeit 15 Monate).", "float", 0.0015, 0, 0.01),
    SettingDef("model.reg", "Modell (wirkt nach „Modelle neu berechnen“)", "Regularisierung",
               "Zieht Teamstärken zum Mittelwert; höher = vorsichtigere Prognosen.", "float", 10.0, 0, 100),
    SettingDef("model.window_days", "Modell (wirkt nach „Modelle neu berechnen“)", "Trainingsfenster (Tage)",
               "Wie weit zurück Spiele ins Training eingehen.", "int", 3 * 365, 180, 3650),
    SettingDef("model.promoted_attack", "Modell (wirkt nach „Modelle neu berechnen“)", "Aufsteiger-Prior Angriff",
               "Startwert für Teams ohne Spiel in der Liga im letzten Jahr.", "float", -0.3, -1, 1),
    SettingDef("model.promoted_defence", "Modell (wirkt nach „Modelle neu berechnen“)", "Aufsteiger-Prior Abwehr",
               "Startwert für Teams ohne Spiel in der Liga im letzten Jahr.", "float", -0.3, -1, 1),
    SettingDef("model.joint", "Modell (wirkt nach „Modelle neu berechnen“)", "Gemeinsames Modell über Ligen (0/1)",
               "1 = Ligen, die durch Auf-/Absteiger verbunden sind, werden gemeinsam gerechnet (eine Stärkeskala, "
               "Aufsteiger behalten ihre Stärke aus der unteren Liga). Nachweis: docs/14_gemeinsames_modell.md.",
               "int", 1, 0, 1),
    SettingDef("api.quota_reserve", "API-Quota", "API-Football: Tagesreserve",
               "So viele Requests pro Tag bleiben für Quoten-Snapshots frei; Importe brechen vorher ab.", "int",
               500, 0, 7000),
    SettingDef("api.max_rps", "API-Quota", "API-Football: Requests pro Sekunde",
               "Drosselung (Limit 300/min; Überschreitung kann zur Firewall-Sperre führen).", "float", 4.0, 0.5, 4.5),
    SettingDef("oddspapi.request_reserve", "API-Quota", "OddsPapi: Monatsreserve",
               "Abrechenbare Requests pro Monat, die nie verbraucht werden (Free-Plan: 250).", "int", 20, 0, 240),
    SettingDef("backup.keep", "Backup", "Backups behalten", "Anzahl Backups unter backups/ (ältere werden gelöscht).",
               "int", 5, 1, 50),
    SettingDef("backup.update_seed", "Backup", "Seed aktualisieren (0/1)", "1 = jedes Backup ersetzt auch "
               "seed/quotenfabrik_seed.dump – per git commit dauerhaft gesichert.", "int", 1, 0, 1),
]  # fmt: skip
BY_KEY = {s.key: s for s in SETTINGS}


class SettingsError(ValueError):
    pass


# --------------------------------------------------------------------------- cached reads

_cache: dict[str, tuple[float, Any]] = {}


def _cached(name: str, loader):
    hit = _cache.get(name)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
        return hit[1]
    value = loader()
    _cache[name] = (time.monotonic(), value)
    return value


def invalidate() -> None:
    _cache.clear()


def _query(sql: str, engine: Engine | None = None) -> list:
    try:
        with (engine or get_engine()).connect() as conn:
            return list(conn.execute(text(sql)))
    except (ProgrammingError, OperationalError):  # schema "app" not migrated yet / database not reachable
        return []


# --------------------------------------------------------------------------- settings


def overrides() -> dict[str, Any]:
    return _cached("settings", lambda: {k: v for k, v in _query("select key, value from app.settings")})


def get(key: str) -> Any:
    return overrides().get(key, BY_KEY[key].default)


def all_values() -> dict[str, Any]:
    o = overrides()
    return {s.key: o.get(s.key, s.default) for s in SETTINGS}


def validate(values: dict[str, Any]) -> dict[str, Any]:
    """Type-checks and clamps nothing: values outside the range are rejected with a German message."""
    clean: dict[str, Any] = {}
    for key, raw in values.items():
        d = BY_KEY.get(key)
        if d is None:
            raise SettingsError(f"Unbekannte Einstellung: {key}")
        if d.type == "choice":
            if raw not in d.choices:
                raise SettingsError(f"{d.label}: erlaubt sind {', '.join(d.choices)}")
            clean[key] = raw
            continue
        try:
            value = int(raw) if d.type == "int" else float(raw)
        except (TypeError, ValueError):
            raise SettingsError(f"{d.label}: Zahl erwartet") from None
        if (d.min is not None and value < d.min) or (d.max is not None and value > d.max):
            raise SettingsError(f"{d.label}: erlaubt {d.min} – {d.max}")
        clean[key] = value
    merged = {**all_values(), **clean}
    for key, label in PROFILE_KEYS.items():
        if merged[f"picks.{key}.min_p"] >= merged[f"picks.{key}.max_p"]:
            raise SettingsError(f"Profil {label}: „ab“ muss kleiner als „bis“ sein")
    return clean


def save(values: dict[str, Any], engine: Engine | None = None) -> dict[str, Any]:
    clean = validate(values)
    with (engine or get_engine()).begin() as conn:
        for key, value in clean.items():
            if value == BY_KEY[key].default:
                conn.execute(text("delete from app.settings where key = :k"), {"k": key})
            else:
                conn.execute(
                    text("""insert into app.settings (key, value, updated_at) values (:k, cast(:v as jsonb), now())
                            on conflict (key) do update set value = excluded.value, updated_at = now()"""),
                    {"k": key, "v": _json(value)},
                )  # fmt: skip
    invalidate()
    return all_values()


def _json(value: Any) -> str:
    return json.dumps(value)


def model_pool(engine, league_id: int):
    """Matches the models of ``league_id`` are fitted on: with ``model.joint`` all configured leagues linked
    to it by shared teams (``league_id`` column, joint model), otherwise the league alone."""
    from quotenfabrik.analytics.data import connected_leagues, load_leagues, load_matches

    if get("model.joint"):
        candidates = [lg.id for lg in all_leagues() if lg.kind == "full"] + [
            lg.id for lg in ratings_leagues()
        ]
        linked = connected_leagues(engine, league_id, candidates)
        if len(linked) > 1:
            ratings = {lg.id for lg in ratings_leagues()}
            return load_leagues(engine, linked, all_rounds=ratings)
    return load_matches(engine, league_id)


def model_params():
    """Poisson model parameters from the configuration page (defaults = PoissonParams defaults)."""
    from quotenfabrik.analytics.poisson import PoissonParams

    return PoissonParams(
        xi=get("model.xi"),
        reg=get("model.reg"),
        window_days=get("model.window_days"),
        promoted_attack=get("model.promoted_attack"),
        promoted_defence=get("model.promoted_defence"),
    )


def effective_settings(base: Settings | None = None) -> Settings:
    """Environment settings with the reserves / throttling from the configuration page applied."""
    base = base or get_settings()
    return base.model_copy(
        update={
            "api_quota_reserve": get("api.quota_reserve"),
            "api_max_rps": get("api.max_rps"),
            "oddspapi_request_reserve": get("oddspapi.request_reserve"),
        }
    )


# --------------------------------------------------------------------------- leagues


@dataclass(frozen=True)
class LeagueConfig:
    id: int
    name: str
    country: str | None
    fd_code: str | None
    oddspapi_tournament: int | None
    first_season: int
    active: bool = True
    kind: str = "full"  # 'ratings' = results only (strength scale), not shown and not forecast


def _env_leagues() -> list[LeagueConfig]:
    s = get_settings()
    fd = dict(zip(s.leagues, s.fd_leagues, strict=False))
    tournaments = dict(zip(s.leagues, s.oddspapi_tournaments, strict=False))
    return [
        LeagueConfig(lid, f"Liga {lid}", None, fd.get(lid), tournaments.get(lid), 2015) for lid in s.leagues
    ]


def all_leagues() -> list[LeagueConfig]:
    """All configured leagues (incl. inactive), in the order they were added."""

    def load():
        rows = _query(
            """select id, name, country, fd_code, oddspapi_tournament, first_season, active, kind
               from app.leagues order by added_at, id"""
        )
        return [LeagueConfig(*r) for r in rows] or _env_leagues()

    return _cached("leagues", load)


def leagues() -> list[LeagueConfig]:
    """Active full leagues: shown in the frontend, forecast, odds snapshots, cron updates."""
    return [lg for lg in all_leagues() if lg.active and lg.kind == "full"]


def ratings_leagues() -> list[LeagueConfig]:
    """Active results-only leagues (strength scale for the joint model)."""
    return [lg for lg in all_leagues() if lg.active and lg.kind == "ratings"]


def league_ids() -> list[int]:
    return [lg.id for lg in leagues()]


def league(league_id: int) -> LeagueConfig:
    for lg in all_leagues():
        if lg.id == league_id:
            return lg
    return LeagueConfig(league_id, f"Liga {league_id}", None, None, None, 2015, active=False)


def fd_code_for(league_id: int) -> str | None:
    return league(league_id).fd_code


def oddspapi_tournament_for(league_id: int) -> int | None:
    return league(league_id).oddspapi_tournament
