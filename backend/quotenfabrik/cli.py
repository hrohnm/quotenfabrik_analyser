"""Command line interface ``qf``."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import typer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from quotenfabrik import app_config, pipeline
from quotenfabrik.config import get_settings
from quotenfabrik.db import get_engine
from quotenfabrik.ingest import odds, oddspapi, quality, rebuild
from quotenfabrik.ingest.db_utils import raw_response_saver
from quotenfabrik.models import OddsPapiFixture
from quotenfabrik.reports import (
    BETANO_REPORT,
    CALIBRATION_REPORT,
    COMBO_REPORT,
    CUP_REPORT,
    FORM_REPORT,
    JOINT_REPORT,
    LINEUP_REPORT,
    ODDS_REPORT,
    PICKS_REPORT,
    SHOTS_REPORT,
    STYLE_REPORT,
    report_path,
)
from quotenfabrik.reports import EVALUATION_REPORT as DEFAULT_REPORT
from quotenfabrik.sources.api_football import ApiFootballClient, QuotaExhausted
from quotenfabrik.sources.oddspapi import OddsPapiClient, OddsPapiQuotaExhausted

app = typer.Typer(help="Quotenfabrik Analyser", no_args_is_help=True)
ingest_app = typer.Typer(help="Daten importieren", no_args_is_help=True)
odds_app = typer.Typer(help="Quoten-Archiv (API-Football)", no_args_is_help=True)
oddspapi_app = typer.Typer(help="Betano-Quoten über OddsPapi", no_args_is_help=True)
model_app = typer.Typer(help="Modelle, Prognosen und Evaluation (Phase 2)", no_args_is_help=True)
combos_app = typer.Typer(help="Tageskombis (Über-Tore, Team-Tore, Doppelte Chance)", no_args_is_help=True)
seed_app = typer.Typer(help="Datenbank-Seed exportieren/importieren", no_args_is_help=True)
value_app = typer.Typer(help="Value-Suche mit Quoten (Phase 3)", no_args_is_help=True)
picks_app = typer.Typer(help="3 Tipps pro Spiel und ihre Trefferquote", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")
app.add_typer(odds_app, name="odds")
app.add_typer(oddspapi_app, name="oddspapi")
app.add_typer(model_app, name="model")
app.add_typer(value_app, name="value")
app.add_typer(picks_app, name="picks")
app.add_typer(seed_app, name="seed")
app.add_typer(combos_app, name="combos")


def _seasons(spec: str) -> list[int]:
    """'2015-2026', '2024,2026' or 'aktuell' (season running now) -> list of season start years."""
    seasons: list[int] = []
    for part in spec.split(","):
        if part.strip().lower() in ("aktuell", "current"):
            from quotenfabrik.jobs import current_season

            seasons.append(current_season())
        elif "-" in part:
            start, end = part.split("-")
            seasons.extend(range(int(start), int(end) + 1))
        elif part.strip():
            seasons.append(int(part))
    return seasons


def _leagues(league: int | None) -> list[int]:
    return [league] if league else app_config.league_ids()


def _model_leagues(league: int | None) -> list[int]:
    """Leagues and European cups that get forecasts and picks."""
    return [league] if league else app_config.shown_league_ids()


def _report(path: Path | None, league_id: int) -> Path | None:
    return report_path(path, league_id)


def _client() -> ApiFootballClient:
    return ApiFootballClient(on_response=raw_response_saver(get_engine()))


def _current_season() -> int:
    now = datetime.now(UTC)
    return now.year if now.month >= 7 else now.year - 1


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


@app.command()
def status() -> None:
    """API-Quota und Abo-Status (kostet keine Quota)."""
    with _client() as client:
        info = client.status()
    sub, req = info.get("subscription", {}), info.get("requests", {})
    typer.echo(f"Plan: {sub.get('plan')}  aktiv: {sub.get('active')}  Ende: {sub.get('end')}")
    typer.echo(f"Requests heute: {req.get('current')} / {req.get('limit_day')}")
    end = sub.get("end")
    if end:
        days = (datetime.fromisoformat(end) - datetime.now(UTC)).days
        if days <= 7:
            typer.secho(f"WARNUNG: Abo endet in {days} Tagen (keine automatische Verlängerung)!", fg="red")


@ingest_app.command("football-data")
def ingest_football_data(
    seasons: str = typer.Option("2015-2026", help="Saison-Startjahre, z. B. 2015-2026 oder aktuell"),
    league: int | None = typer.Option(None, help="API-Liga-ID (Standard: konfigurierte Ligen)"),
) -> None:
    """Historische Ergebnisse + Quoten von football-data.co.uk (keine API-Quota)."""
    with Session(get_engine()) as session:
        for league_id in _leagues(league):
            result = pipeline.football_data_seasons(session, league_id, _seasons(seasons), log=typer.echo)
            typer.echo(f"Liga {league_id}: {result}")


@ingest_app.command("api-football")
def ingest_api_football(
    seasons: str = typer.Option("2015-2026", help="Saison-Startjahre, z. B. 2015-2026 oder aktuell"),
    league: int | None = typer.Option(None, help="API-Liga-ID (Standard: konfigurierte Ligen)"),
    details: bool = typer.Option(True, help="Events, Lineups, Stats und Spieler-Stats laden"),
    half_stats: bool = typer.Option(False, "--half-stats", help="Halbzeit-Stats ab 2024 (1 Request/Spiel)"),
    injuries: bool = typer.Option(True, help="Verletzungen/Ausfälle (ab 2021)"),
) -> None:
    """Spielplan, Ergebnisse und Spieldetails von API-Football."""
    with Session(get_engine()) as session, _client() as client:
        try:
            for league_id in _leagues(league):
                result = pipeline.api_football_seasons(
                    session, client, league_id, _seasons(seasons), details=details, half_stats=half_stats,
                    injuries=injuries, log=lambda m, lid=league_id: typer.echo(f"Liga {lid} {m}"),
                )  # fmt: skip
                typer.echo(f"Liga {league_id}: {result}")
        except QuotaExhausted as exc:
            typer.secho(f"Abgebrochen: {exc}", fg="red")


@ingest_app.command("live")
def ingest_live() -> None:
    """Ergebnisse von Spielen, deren reguläres Ende erreicht ist (Cron alle 15 Minuten), danach
    Prognosen, Tipps und Wetten abrechnen; dazu bestätigte Aufstellungen der Spiele der nächsten Stunde.
    Ohne fällige Spiele kein Request."""
    from quotenfabrik.ingest import api_football

    leagues = app_config.shown_league_ids()
    with Session(get_engine()) as session:
        if not (
            api_football.fixtures_due(session, leagues) or api_football.fixtures_lineup_due(session, leagues)
        ):
            typer.echo("keine fälligen Spiele")
            return
        with _client() as client:
            try:
                typer.echo(pipeline.live_results(get_engine(), session, client, leagues, typer.echo))
            except QuotaExhausted as exc:
                typer.secho(f"Abgebrochen: {exc}", fg="red")


@ingest_app.command("results")
def ingest_results(
    seasons: str = typer.Option("aktuell", help="Saison-Startjahre, z. B. aktuell oder 2017-2026"),
    league: int | None = typer.Option(None, help="API-Liga-ID (Standard: aktive Stärke-Ligen)"),
) -> None:
    """Ergebnisse der Stärke-Ligen und Europapokale (1 Request pro Saison und Wettbewerb); Europapokale der
    letzten zwei Saisons zusätzlich mit Spieldetails für Torschützen (20 Spiele pro Request)."""
    ids = [league] if league else [lg.id for lg in app_config.ratings_leagues() + app_config.cup_leagues()]
    if not ids:
        typer.echo("Keine Stärke-Ligen konfiguriert.")
        return
    with Session(get_engine()) as session, _client() as client:
        try:
            for league_id in ids:
                result = pipeline.results_seasons(session, client, league_id, _seasons(seasons))
                typer.echo(f"Liga {league_id}: {result}")
        except QuotaExhausted as exc:
            typer.secho(f"Abgebrochen: {exc}", fg="red")


@app.command("map-teams")
def map_teams(league: int | None = typer.Option(None)) -> None:
    """football-data-Teamnamen auf API-Team-IDs mappen und Spiele verknüpfen."""
    with Session(get_engine()) as session:
        for league_id in _leagues(league):
            typer.echo(f"Liga {league_id}: {pipeline.map_teams(session, league_id, log=typer.echo)}")


@odds_app.command("snapshot")
def odds_snapshot(league: int | None = typer.Option(None), season: int | None = typer.Option(None)) -> None:
    """Aktuelle Pre-Match-Quoten speichern (nur Änderungen, nur konfigurierte Buchmacher)."""
    with Session(get_engine()) as session, _client() as client:
        odds.seed_bet_types(session)
        for league_id in _leagues(league):
            result = odds.snapshot(session, client, league_id, season or _current_season())
            typer.echo(f"Liga {league_id}: {result['pages']} Seiten, {result['rows']} geänderte Quoten")


@odds_app.command("reference-data")
def odds_reference_data() -> None:
    """Buchmacher- und Wettarten-Stammdaten laden (2 Requests)."""
    with Session(get_engine()) as session, _client() as client:
        odds.sync_reference_data(session, client)
    typer.echo("Buchmacher und Wettarten aktualisiert")


# --------------------------------------------------------------------------- OddsPapi


def _oddspapi_echo_quota(client: OddsPapiClient) -> None:
    typer.echo(
        f"OddsPapi: {client.billable_requests_made} abrechenbare Requests in diesem Lauf, "
        f"Monat: {client.requests_used} / {client.request_limit}"
    )


@oddspapi_app.command("status")
def oddspapi_status() -> None:
    """Plan und Monatsverbrauch (kostenlos)."""
    with OddsPapiClient() as client:
        info = client.account()
    typer.echo(
        f"Plan: {info['plan']}  Requests diesen Monat: {info['request_count']} / {info['request_limit']}"
    )
    wanted = set(get_settings().oddspapi_bookmakers)
    missing = wanted - set(info["bookmakers"])
    typer.echo(f"Buchmacher im Plan: {', '.join(sorted(wanted & set(info['bookmakers'])))}")
    if missing:
        typer.secho(f"Nicht im Plan: {', '.join(sorted(missing))}", fg="red")


@oddspapi_app.command("markets")
def oddspapi_markets() -> None:
    """Marktkatalog laden (1 Request)."""
    with Session(get_engine()) as session, OddsPapiClient() as client:
        count = oddspapi.sync_markets(session, client)
        typer.echo(f"{count} Märkte, davon verfolgt: {len(oddspapi.tracked_market_ids(session))}")
        _oddspapi_echo_quota(client)


@oddspapi_app.command("fixtures")
def oddspapi_fixtures(
    date_from: str = typer.Option("2026-01-01", "--from", help="Startdatum YYYY-MM-DD"),
    date_to: str | None = typer.Option(None, "--to", help="Enddatum (Standard: heute + 60 Tage)"),
    league: int | None = typer.Option(None),
) -> None:
    """Spielplan von OddsPapi laden und mit API-Football verknüpfen (1 Request pro Liga)."""
    start = datetime.fromisoformat(date_from).replace(tzinfo=UTC)
    end = datetime.fromisoformat(date_to).replace(tzinfo=UTC) if date_to else None
    with Session(get_engine()) as session, OddsPapiClient() as client:
        for league_id in _leagues(league):
            result = pipeline.oddspapi_fixtures(session, client, league_id, start, end, log=typer.echo)
            typer.echo(f"Liga {league_id}: {result}")
        _oddspapi_echo_quota(client)


def _oddspapi_map(session: Session, league_id: int, tournament: int) -> None:
    r = oddspapi.map_fixtures(session, league_id, tournament)
    typer.echo(f"  Teams: {r.aliases_total} gemappt ({r.aliases_new} neu), Spiele verknüpft: {r.linked}")
    for line in r.unlinked[:20]:
        typer.secho(f"  nicht verknüpft: {line}", fg="yellow")


@oddspapi_app.command("history")
def oddspapi_history(
    league: int | None = typer.Option(None),
    limit: int | None = typer.Option(None, help="Maximal so viele Spiele (Test)"),
) -> None:
    """Quotenverläufe (Betano + Pinnacle) aller offenen Spiele seit 01/2026 laden (kostenlos, 5 s/Spiel)."""
    with Session(get_engine()) as session, OddsPapiClient() as client:
        for league_id in _leagues(league):
            result = pipeline.oddspapi_history(session, client, league_id, limit, typer.echo)
            typer.echo(f"Liga {league_id}: {result}")


@oddspapi_app.command("players")
def oddspapi_players(league: int | None = typer.Option(None)) -> None:
    """Spielernamen für Torschützen-Märkte der kommenden Spiele (1 Request pro Liga)."""
    get_settings()
    with Session(get_engine()) as session, OddsPapiClient() as client:
        for league_id in _leagues(league):
            tournament = app_config.oddspapi_tournament_for(league_id)
            if not tournament:
                continue
            count = oddspapi.sync_player_names(session, client, tournament)
            typer.echo(f"Liga {league_id}: {count} Spielernamen")
        _oddspapi_echo_quota(client)


@oddspapi_app.command("update")
def oddspapi_update(league: int | None = typer.Option(None)) -> None:
    """Laufender Betrieb: Spielplan wöchentlich auffrischen (1 Request), dann Verläufe laden (kostenlos)."""
    settings = get_settings()
    with Session(get_engine()) as session, OddsPapiClient() as client:
        try:
            for league_id in _leagues(league):
                tournament = app_config.oddspapi_tournament_for(league_id)
                if not tournament:
                    continue
                last = session.scalar(
                    select(func.max(OddsPapiFixture.updated_at)).where(
                        OddsPapiFixture.tournament_id == tournament
                    )
                )
                now = datetime.now(UTC)
                if last is None or now - last > timedelta(days=6):
                    count = oddspapi.sync_fixtures(
                        session, client, tournament, now - timedelta(days=7), now + timedelta(days=60)
                    )
                    typer.echo(f"Liga {league_id}: Spielplan aktualisiert ({count} Spiele)")
                    _oddspapi_map(session, league_id, tournament)
                fixtures = oddspapi.fixtures_needing_history(session, tournament)
                stats = oddspapi.sync_history(session, client, fixtures, settings.oddspapi_bookmakers)
                typer.echo(f"Liga {league_id}: {stats['fixtures']} Verläufe ({stats['final']} abgeschlossen)")
        except OddsPapiQuotaExhausted as exc:
            typer.secho(f"Abgebrochen: {exc}", fg="red")
        _oddspapi_echo_quota(client)


# --------------------------------------------------------------------------- models (phase 2)


@model_app.command("evaluate")
def model_evaluate(
    seasons: str = typer.Option("2022-2026", help="Testsaisons (Walk-Forward), z. B. 2022-2026"),
    league: int | None = typer.Option(None),
    report: Path | None = typer.Option(DEFAULT_REPORT, help="Markdown-Bericht"),
) -> None:
    """Walk-Forward-Evaluation aller Marktgruppen ohne Quoten, speichert Kennzahlen und Bericht."""
    from quotenfabrik.analytics.service import run_evaluation

    for league_id in _leagues(league):
        path = _report(report, league_id)
        result = run_evaluation(get_engine(), league_id, _seasons(seasons), report_path=path)
        typer.echo(f"Liga {league_id}: {result}" + (f" · Bericht: {path}" if path else ""))


@model_app.command("joint-eval")
def model_joint_eval(
    validation: str = typer.Option("2018-2020", help="Validierungssaisons"),
    test: str = typer.Option("2021-2026", help="Testsaisons"),
    league: int | None = typer.Option(None, help="Ausgangsliga (Standard: erste konfigurierte)"),
    report: Path = typer.Option(JOINT_REPORT, help="Markdown-Bericht"),
) -> None:
    """Gemeinsames Modell über verbundene Ligen gegen getrennte Modelle (Walk-Forward) → Bericht."""
    from quotenfabrik.analytics import joint_eval
    from quotenfabrik.analytics.data import connected_leagues, league_name, load_leagues
    from quotenfabrik.app_config import model_params

    engine = get_engine()
    start = league or app_config.league_ids()[0]
    leagues = connected_leagues(engine, start, [lg.id for lg in app_config.all_leagues()])
    if len(leagues) < 2:
        typer.secho(
            f"Liga {start} teilt keine Teams mit anderen konfigurierten Ligen – nichts zu vergleichen.",
            fg="red",
        )
        raise typer.Exit(1)
    names = {lg: league_name(engine, lg) for lg in leagues}
    text = joint_eval.report(
        load_leagues(engine, leagues), leagues, names, _seasons(validation), _seasons(test), model_params()
    )
    report.write_text(text, encoding="utf-8")
    typer.echo(f"Bericht: {report}")


@model_app.command("form-eval")
def model_form_eval(report: Path = typer.Option(FORM_REPORT, help="Markdown-Bericht")) -> None:
    """Form-Pattern (Punkte über/unter Modell-Erwartung, alle Wettbewerbe) gegen das nächste Spiel prüfen."""
    import pandas as pd

    from quotenfabrik.analytics import form

    history = form.load_history(get_engine(), pd.Timestamp.now(tz="UTC"), kinds=("backtest",))
    result = form.evaluate(form.team_rows(history))
    report.write_text(form.report(result), encoding="utf-8")
    typer.echo(f"{result['n']} Spiele ausgewertet → {report}")


@model_app.command("style-eval")
def model_style_eval(report: Path = typer.Option(STYLE_REPORT, help="Markdown-Bericht")) -> None:
    """Spielstil (Schüsse, Ballbesitz, Verwertung, …) gegen die Tor-Erwartung des Modells prüfen."""
    from quotenfabrik.analytics import style_eval
    from quotenfabrik.analytics.data import league_name

    ids = app_config.league_ids()
    result = style_eval.evaluate(get_engine(), ids)
    report.write_text(
        style_eval.report(result, [league_name(get_engine(), i) for i in ids]), encoding="utf-8"
    )
    typer.echo(f"{result['n']} Team-Spiele ausgewertet → {report}")


@model_app.command("shots-eval")
def model_shots_eval(
    validation: str = typer.Option("2018-2020", help="Validierungssaisons (Auswahl der Variante)"),
    test: str = typer.Option("2021-2026", help="Testsaisons"),
    report: Path = typer.Option(SHOTS_REPORT, help="Markdown-Bericht"),
) -> None:
    """Schüsse im Tor-Modell (Mischung aus Toren und Schuss-Erwartung) gegen das reine Tor-Modell prüfen."""
    from quotenfabrik.analytics import shots_eval
    from quotenfabrik.analytics.data import league_name

    engine = get_engine()
    start = app_config.league_ids()[0]
    pool = app_config.model_pool(engine, start)
    leagues = sorted(int(lg) for lg in pool["league_id"].unique()) if "league_id" in pool.columns else [start]
    if "league_id" not in pool.columns:
        pool = pool.assign(league_id=start)
    result = shots_eval.evaluate(
        pool, leagues, _seasons(validation), _seasons(test), app_config.model_params()
    )
    report.write_text(
        shots_eval.report(result, {lg: league_name(engine, lg) for lg in leagues}), encoding="utf-8"
    )
    typer.echo(f"gewählt: {result['best']}, Δ Log-Loss 1X2 {result['delta']} → {report}")


@model_app.command("lineup-eval")
def model_lineup_eval(
    seasons: str = typer.Option("2021-2026", help="Saisons (Ausfälle gibt es ab 2021)"),
    report: Path = typer.Option(LINEUP_REPORT, help="Markdown-Bericht"),
) -> None:
    """Voraussichtliche Startelf (letzte Startelf, Ausfälle ersetzt) gegen die bestätigte prüfen."""
    from quotenfabrik.analytics import lineups
    from quotenfabrik.analytics.data import league_name

    engine = get_engine()
    leagues, season_list = app_config.league_ids(), _seasons(seasons)
    fixtures = lineups.load_eval_fixtures(engine, leagues, season_list)
    absences = lineups.load_absences(engine, fixtures["fixture_id"].unique().tolist())
    result = lineups.evaluate(lineups.load_history(engine), absences, fixtures)
    report.write_text(
        lineups.report(result, {lg: league_name(engine, lg) for lg in leagues}, season_list), encoding="utf-8"
    )
    means = ", ".join(f"{v}: {result[v].mean():.2f}" for v in lineups.VARIANTS)
    typer.echo(f"{len(result)} Startelfen, richtig im Schnitt {means} → {report}")


@model_app.command("calibration-eval")
def model_calibration_eval(
    seasons: str = typer.Option("2018-2026", help="Testsaisons (jede mit den Saisons davor kalibriert)"),
    report: Path = typer.Option(CALIBRATION_REPORT, help="Markdown-Bericht"),
) -> None:
    """Kalibrierung (Nachkorrektur je Markt) gegen die rohen Prognosen prüfen (Backtest nötig)."""
    from quotenfabrik.analytics import calibration
    from quotenfabrik.analytics.data import league_name
    from quotenfabrik.analytics.evaluation import market_group_of

    engine = get_engine()
    results = {}
    for league_id in app_config.league_ids():
        preds = calibration.load_backtest(engine, league_id)
        results[league_name(engine, league_id)] = calibration.walk_forward(preds, _seasons(seasons))
        typer.echo(f"Liga {league_id}: {len(results[league_name(engine, league_id)])} Prognosen")
    report.write_text(calibration.report(results, market_group_of), encoding="utf-8")
    typer.echo(f"→ {report}")


@model_app.command("cup-eval")
def model_cup_eval(
    validation: str = typer.Option("2019-2021", help="Validierungssaisons (Pokalsaison = Startjahr)"),
    test: str = typer.Option("2022-2026", help="Testsaisons"),
    league_test: str = typer.Option(
        "2021-2026", help="Testsaisons der eigenen Ligen (Auswirkung auf deren Prognosen)"
    ),
    workers: int = typer.Option(4, help="Parallele Prozesse"),
    report: Path = typer.Option(CUP_REPORT, help="Markdown-Bericht"),
) -> None:
    """Europapokal: gemeinsames Modell über alle Ligen und Pokale, Walk-Forward auf Pokalspielen → Bericht."""
    import pandas as pd

    from quotenfabrik.analytics import cup_eval
    from quotenfabrik.analytics.data import league_name, season_leagues
    from quotenfabrik.analytics.poisson import fit_poisson
    from quotenfabrik.app_config import model_params

    full = [lg.id for lg in app_config.all_leagues() if lg.kind == "full"]
    ratings = [lg.id for lg in app_config.ratings_leagues()]
    cups = [lg.id for lg in app_config.cup_leagues()]
    if not cups:
        typer.secho(
            "Keine Europapokale konfiguriert (Einstellungen → Stärke-Ligen und Europapokal).", fg="red"
        )
        raise typer.Exit(1)
    params = model_params()
    seasons = (_seasons(validation), _seasons(test), _seasons(league_test))
    results = cup_eval.run(full, ratings, cups, *seasons, params, workers=workers)
    engine = get_engine()
    names = {lg: league_name(engine, lg) for lg in full + ratings}
    for lg in app_config.all_leagues():
        if lg.kind == "ratings" and lg.country:
            names[lg.id] = f"{names[lg.id]} ({lg.country})"
    pool = cup_eval.load_pool(engine, full, ratings, cups)
    now = pd.Timestamp.now(tz="UTC")
    latest = season_leagues(pool)
    fitted = fit_poisson(pool, now, params, "hg", "ag", None, "hxg", "axg", team_league=latest[max(latest)])
    levels = sorted(((names.get(lg, str(lg)), fitted.league_attack[lg] + fitted.league_defence[lg])
                     for lg in fitted.league_attack), key=lambda x: -x[1])  # fmt: skip
    text = cup_eval.report(
        {v: results["cup"][("validation", v)] for v in cup_eval.VARIANTS},
        {v: results["cup"][("test", v)] for v in cup_eval.VARIANTS},
        _seasons(validation), _seasons(test), levels, cup_eval.league_section(results, names),
    )  # fmt: skip
    report.write_text(text, encoding="utf-8")
    typer.echo(f"Bericht: {report}")


@model_app.command("forecast")
def model_forecast(
    days: int = typer.Option(10, help="Spiele der nächsten N Tage"),
    league: int | None = typer.Option(None),
) -> None:
    """Prognosen und Pattern für kommende Spiele berechnen und speichern."""
    from quotenfabrik.analytics.picks import build_picks
    from quotenfabrik.analytics.service import run_forecast

    for league_id in _model_leagues(league):
        result = run_forecast(get_engine(), league_id, days)
        if "model_run_id" in result:
            result["picks"] = build_picks(get_engine(), league_id, result["model_run_id"])["picks"]
        typer.echo(f"Liga {league_id}: {result}")


@model_app.command("backtest")
def model_backtest(
    seasons: str = typer.Option("2016-2026", help="Saisons mit rückwirkenden Prognosen (Walk-Forward)"),
    league: int | None = typer.Option(None),
) -> None:
    """Rückwirkende Prognosen aller beendeten Spiele speichern (für Daten-Explorer und Auswertung)."""
    from quotenfabrik.analytics.picks import build_picks
    from quotenfabrik.analytics.service import run_backtest

    for league_id in _model_leagues(league):
        result = run_backtest(get_engine(), league_id, _seasons(seasons))
        result["picks"] = build_picks(get_engine(), league_id, result["model_run_id"])["picks"]
        typer.echo(f"Liga {league_id}: {result}")


@model_app.command("settle")
def model_settle(league: int | None = typer.Option(None)) -> None:
    """Ergebnis (zugetroffen ja/nein) für Prognosen beendeter Spiele eintragen."""
    from quotenfabrik.analytics.service import settle_predictions

    for league_id in _model_leagues(league):
        typer.echo(f"Liga {league_id}: {settle_predictions(get_engine(), league_id)} Prognosen abgerechnet")


@model_app.command("show")
def model_show(fixture: int = typer.Argument(..., help="API-Football Fixture-ID")) -> None:
    """Letzte Prognose eines Spiels anzeigen (Hauptmärkte, Top-Torschützen, Pattern-Signale)."""
    from quotenfabrik.analytics.service import show_fixture

    typer.echo(show_fixture(get_engine(), fixture))


# --------------------------------------------------------------------------- value (phase 3)


@value_app.command("backtest")
def value_backtest(
    validation_until: int = typer.Option(2021, help="letzte Validierungssaison, danach Test"),
    method: str = typer.Option("shin", help="Margenentfernung: shin, power oder proportional"),
    league: int | None = typer.Option(None),
    report: Path | None = typer.Option(ODDS_REPORT, help="Markdown-Bericht"),
) -> None:
    """Prognosen (qf model backtest) gegen historische Quoten: 1X2 und Ü/U 2,5, ROI, CLV, Marktvergleich."""
    from quotenfabrik.analytics.odds_report import run_odds_backtest

    for league_id in _leagues(league):
        path = _report(report, league_id)
        result = run_odds_backtest(get_engine(), league_id, validation_until, method, path)
        typer.echo(f"Liga {league_id}: {result}" + (f" · Bericht: {path}" if path else ""))


@value_app.command("betano")
def value_betano(
    league: int | None = typer.Option(None),
    report: Path | None = typer.Option(BETANO_REPORT, help="Markdown-Bericht"),
) -> None:
    """Betano-Nebenmärkte gegen faire Preise aus Pinnacle (Marktmodell mkt-v1): Edge, CLV, Margen."""
    from quotenfabrik.analytics.betano_report import run_betano_value

    for league_id in _leagues(league):
        path = _report(report, league_id)
        result = run_betano_value(get_engine(), league_id, path)
        typer.echo(f"Liga {league_id}: {result}" + (f" · Bericht: {path}" if path else ""))


# --------------------------------------------------------------------------- picks


@combos_app.command("report")
def combos_report(report: Path = typer.Option(COMBO_REPORT, help="Markdown-Bericht")) -> None:
    """Tageskombis: Erfolgschance auf den rückwirkenden Prognosen aller Ligen und Pokale → Bericht."""
    from quotenfabrik.analytics import combos
    from quotenfabrik.analytics.data import league_name

    engine = get_engine()
    leagues = app_config.shown_league_ids()
    preds = combos.load_backtest(engine, leagues)
    names = [league_name(engine, lg) for lg in leagues]
    report.write_text(combos.report(preds, app_config.combo_settings(), names), encoding="utf-8")
    typer.echo(f"Bericht: {report}")


@picks_app.command("build")
def picks_build(
    league: int | None = typer.Option(None),
    if_empty: bool = typer.Option(False, "--if-empty", help="nur, wenn noch keine Tipps gespeichert sind"),
) -> None:
    """3 Tipps pro Spiel und Profil für alle Prognosen (Backtest und Forecast) berechnen und speichern."""
    from quotenfabrik.analytics.picks import build_picks, picks_missing

    if if_empty and not picks_missing(get_engine()):
        typer.echo("Tipps vorhanden – nichts zu tun.")
        return
    for league_id in _model_leagues(league):
        typer.echo(f"Liga {league_id}: {build_picks(get_engine(), league_id)}")


@picks_app.command("report")
def picks_report(
    league: int | None = typer.Option(None),
    validation_until: int = typer.Option(2021, help="letzte Saison, auf der die Profile gewählt wurden"),
    report: Path = typer.Option(PICKS_REPORT, help="Markdown-Bericht"),
) -> None:
    """Trefferquote der Tipps (einzeln und als Dreier-Kombi) → docs/12_tipps.md."""
    from quotenfabrik.analytics.picks_report import write_report

    for league_id in _leagues(league):
        path = _report(report, league_id)
        write_report(get_engine(), league_id, validation_until, path)
        typer.echo(f"Liga {league_id}: Bericht {path}")


# --------------------------------------------------------------------------- jobs / backup

jobs_app = typer.Typer(help="Hintergrund-Jobs der Konfigurationsseite", no_args_is_help=True)
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("run")
def jobs_run(job_id: int = typer.Argument(..., help="ID aus app.jobs")) -> None:
    """Job ausführen (wird von der Konfigurationsseite als eigener Prozess gestartet)."""
    from quotenfabrik import jobs

    typer.echo(f"Job {job_id}: {jobs.run(job_id)}")


@app.command("backup")
def backup_cmd(reason: str = typer.Option("manuell", help="Kurzbeschreibung im Dateinamen")) -> None:
    """Datenbank-Backup nach backups/ (und je nach Einstellung auch seed/ aktualisieren)."""
    from quotenfabrik.backup import create_backup

    path = create_backup(reason)
    typer.echo(f"Backup: {path} ({path.stat().st_size / 1e6:.1f} MB)")


# --------------------------------------------------------------------------- seed


@seed_app.command("export")
def seed_export() -> None:
    """Datenbank (raw, core, analytics) nach seed/quotenfabrik_seed.dump schreiben."""
    from quotenfabrik.seed import export_seed

    path = export_seed()
    typer.echo(f"Seed geschrieben: {path} ({path.stat().st_size / 1e6:.1f} MB)")


@seed_app.command("import")
def seed_import(
    force: bool = typer.Option(False, "--force", help="Vorhandene Schemas raw/core/analytics löschen"),
    file: Path | None = typer.Option(
        None, "--file", help="Anderes Dump einspielen, z. B. ein Backup (.revision-Datei daneben)"
    ),
) -> None:
    """Seed in eine leere Datenbank einspielen (statt Import über die APIs)."""
    from quotenfabrik.seed import SEED_FILE, database_is_empty, drop_schemas, import_seed, require_tools

    path = file or SEED_FILE
    if not path.is_file():
        typer.secho(f"Datei nicht gefunden: {path}", fg="red")
        raise typer.Exit(1)
    if file and not path.with_suffix(".revision").is_file():
        revision = path.with_suffix(".revision").name
        typer.secho(f"{revision} fehlt (Schema-Stand des Dumps) – bitte mitkopieren.", fg="red")
        raise typer.Exit(1)
    require_tools("pg_restore")  # check before dropping anything
    if not database_is_empty():
        if not force:
            typer.secho(
                "Datenbank enthält bereits Daten. Mit --force werden raw/core/analytics gelöscht.", fg="red"
            )
            raise typer.Exit(1)
        drop_schemas()
    import_seed(path)
    typer.echo("Seed eingespielt und Schema auf aktuellen Stand gebracht (Seed-Revision + alembic upgrade).")


@app.command("rebuild")
def rebuild_core() -> None:
    """core-Tabellen aus den Rohdaten neu aufbauen (keine API-Quota)."""
    with Session(get_engine()) as session:
        counts = rebuild.rebuild_from_raw(session)
    typer.echo(f"Neu verarbeitet: {counts}")


@app.command("quality")
def quality_report(league: int | None = typer.Option(None)) -> None:
    """Datenqualitäts-Report pro Saison."""
    with Session(get_engine()) as session:
        for league_id in _leagues(league):
            rows = quality.season_report(session, league_id)
            typer.echo(f"Liga {league_id}")
            typer.echo(" | ".join(quality.COLUMNS))
            for row in rows:
                typer.echo(" | ".join(str(row[c]) for c in quality.COLUMNS))


if __name__ == "__main__":
    app()
