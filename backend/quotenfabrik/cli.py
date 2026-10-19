"""Command line interface ``qf``."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import typer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from quotenfabrik.config import get_settings
from quotenfabrik.db import get_engine
from quotenfabrik.ingest import api_football, football_data, odds, oddspapi, quality, rebuild, team_mapping
from quotenfabrik.ingest.db_utils import raw_response_saver
from quotenfabrik.models import OddsPapiFixture
from quotenfabrik.sources.api_football import ApiFootballClient, QuotaExhausted
from quotenfabrik.sources.oddspapi import OddsPapiClient, OddsPapiQuotaExhausted

DEFAULT_REPORT = Path(__file__).resolve().parents[2] / "docs" / "09_modell_evaluation.md"
ODDS_REPORT = Path(__file__).resolve().parents[2] / "docs" / "10_quoten_backtest.md"

app = typer.Typer(help="Quotenfabrik Analyser", no_args_is_help=True)
ingest_app = typer.Typer(help="Daten importieren", no_args_is_help=True)
odds_app = typer.Typer(help="Quoten-Archiv (API-Football)", no_args_is_help=True)
oddspapi_app = typer.Typer(help="Betano-Quoten über OddsPapi", no_args_is_help=True)
model_app = typer.Typer(help="Modelle, Prognosen und Evaluation (Phase 2)", no_args_is_help=True)
seed_app = typer.Typer(help="Datenbank-Seed exportieren/importieren", no_args_is_help=True)
value_app = typer.Typer(help="Value-Suche mit Quoten (Phase 3)", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")
app.add_typer(odds_app, name="odds")
app.add_typer(oddspapi_app, name="oddspapi")
app.add_typer(model_app, name="model")
app.add_typer(value_app, name="value")
app.add_typer(seed_app, name="seed")


def _seasons(spec: str) -> list[int]:
    """'2015-2026' or '2024,2026' -> list of season start years."""
    seasons: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            start, end = part.split("-")
            seasons.extend(range(int(start), int(end) + 1))
        elif part.strip():
            seasons.append(int(part))
    return seasons


def _leagues(league: int | None) -> list[int]:
    return [league] if league else get_settings().leagues


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
    seasons: str = typer.Option("2015-2026", help="Saison-Startjahre, z. B. 2015-2026"),
    league: int | None = typer.Option(None, help="API-Liga-ID (Standard: QF_LEAGUES)"),
) -> None:
    """Historische Ergebnisse + Quoten von football-data.co.uk (keine API-Quota)."""
    settings = get_settings()
    with Session(get_engine()) as session, httpx.Client(timeout=60, follow_redirects=True) as http:
        for league_id in _leagues(league):
            code = settings.fd_code_for(league_id)
            total = sum(football_data.sync_season(session, code, s, http) for s in _seasons(seasons))
            typer.echo(f"{code}: {total} Spiele importiert")


@ingest_app.command("api-football")
def ingest_api_football(
    seasons: str = typer.Option("2015-2026", help="Saison-Startjahre, z. B. 2015-2026"),
    league: int | None = typer.Option(None, help="API-Liga-ID (Standard: QF_LEAGUES)"),
    details: bool = typer.Option(True, help="Events, Lineups, Stats und Spieler-Stats laden"),
    half_stats: bool = typer.Option(False, "--half-stats", help="Halbzeit-Stats ab 2024 (1 Request/Spiel)"),
    injuries: bool = typer.Option(True, help="Verletzungen/Ausfälle (ab 2021)"),
) -> None:
    """Spielplan, Ergebnisse und Spieldetails von API-Football."""
    with Session(get_engine()) as session, _client() as client:
        client.status()
        try:
            for league_id in _leagues(league):
                for season in _seasons(seasons):
                    n = api_football.sync_season(session, client, league_id, season)
                    msg = f"Liga {league_id} {season}: {n} Spiele"
                    if details:
                        missing = api_football.fixtures_missing_details(session, league_id, season)
                        msg += f", Details {api_football.sync_details(session, client, missing)}"
                    if half_stats:
                        missing = api_football.fixtures_missing_half_stats(session, league_id, season)
                        msg += f", Halbzeit-Stats {api_football.sync_half_stats(session, client, missing)}"
                    if injuries and season >= 2021:
                        msg += f", Ausfälle {api_football.sync_injuries(session, client, league_id, season)}"
                    typer.echo(msg)
        except QuotaExhausted as exc:
            typer.secho(f"Abgebrochen: {exc}", fg="red")
        typer.echo(f"API-Requests: {client.requests_made}, verbleibend heute: {client.quota_remaining}")


@app.command("map-teams")
def map_teams(league: int | None = typer.Option(None)) -> None:
    """football-data-Teamnamen auf API-Team-IDs mappen und Spiele verknüpfen."""
    settings = get_settings()
    with Session(get_engine()) as session:
        for league_id in _leagues(league):
            r = team_mapping.map_and_link(session, league_id, settings.fd_code_for(league_id))
            typer.echo(
                f"Liga {league_id}: {r.aliases_total} Aliase ({r.aliases_new} neu), "
                f"{r.rows_linked} Spiele verknüpft, {r.rows_unlinked} offen"
            )
            if r.unmapped_aliases:
                typer.secho(f"  Nicht gemappt: {', '.join(r.unmapped_aliases)}", fg="yellow")
            for example in r.unlinked_examples:
                typer.echo(f"  offen: {example}")


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
    settings = get_settings()
    start = datetime.fromisoformat(date_from).replace(tzinfo=UTC)
    end = (
        datetime.fromisoformat(date_to).replace(tzinfo=UTC)
        if date_to
        else datetime.now(UTC) + timedelta(days=60)
    )
    with Session(get_engine()) as session, OddsPapiClient() as client:
        for league_id in _leagues(league):
            tournament = settings.oddspapi_tournament_for(league_id)
            count = oddspapi.sync_fixtures(session, client, tournament, start, end)
            typer.echo(f"Liga {league_id} / Turnier {tournament}: {count} Spiele")
            _oddspapi_map(session, league_id, tournament)
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
    settings = get_settings()
    with Session(get_engine()) as session, OddsPapiClient() as client:
        if not oddspapi.tracked_market_ids(session):
            typer.echo("Marktkatalog fehlt, lade ihn zuerst (1 Request)")
            oddspapi.sync_markets(session, client)
        for league_id in _leagues(league):
            tournament = settings.oddspapi_tournament_for(league_id)
            fixtures = oddspapi.fixtures_needing_history(session, tournament, limit=limit)
            typer.echo(f"Liga {league_id}: {len(fixtures)} Spiele, ca. {len(fixtures) * 5 // 60 + 1} Minuten")
            stats = oddspapi.sync_history(session, client, fixtures, settings.oddspapi_bookmakers)
            typer.echo(
                f"  {stats['fixtures']} Verläufe geladen ({stats['final']} abgeschlossen, "
                f"{stats['not_found']} ohne Daten), {stats['rows']} Preisänderungen verarbeitet"
            )


@oddspapi_app.command("players")
def oddspapi_players(league: int | None = typer.Option(None)) -> None:
    """Spielernamen für Torschützen-Märkte der kommenden Spiele (1 Request pro Liga)."""
    settings = get_settings()
    with Session(get_engine()) as session, OddsPapiClient() as client:
        for league_id in _leagues(league):
            count = oddspapi.sync_player_names(session, client, settings.oddspapi_tournament_for(league_id))
            typer.echo(f"Liga {league_id}: {count} Spielernamen")
        _oddspapi_echo_quota(client)


@oddspapi_app.command("update")
def oddspapi_update(league: int | None = typer.Option(None)) -> None:
    """Laufender Betrieb: Spielplan wöchentlich auffrischen (1 Request), dann Verläufe laden (kostenlos)."""
    settings = get_settings()
    with Session(get_engine()) as session, OddsPapiClient() as client:
        try:
            for league_id in _leagues(league):
                tournament = settings.oddspapi_tournament_for(league_id)
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
        result = run_evaluation(get_engine(), league_id, _seasons(seasons), report_path=report)
        typer.echo(f"Liga {league_id}: {result}")
    if report:
        typer.echo(f"Bericht: {report}")


@model_app.command("forecast")
def model_forecast(
    days: int = typer.Option(10, help="Spiele der nächsten N Tage"),
    league: int | None = typer.Option(None),
) -> None:
    """Prognosen und Pattern für kommende Spiele berechnen und speichern."""
    from quotenfabrik.analytics.service import run_forecast

    for league_id in _leagues(league):
        typer.echo(f"Liga {league_id}: {run_forecast(get_engine(), league_id, days)}")


@model_app.command("backtest")
def model_backtest(
    seasons: str = typer.Option("2016-2026", help="Saisons mit rückwirkenden Prognosen (Walk-Forward)"),
    league: int | None = typer.Option(None),
) -> None:
    """Rückwirkende Prognosen aller beendeten Spiele speichern (für Daten-Explorer und Auswertung)."""
    from quotenfabrik.analytics.service import run_backtest

    for league_id in _leagues(league):
        typer.echo(f"Liga {league_id}: {run_backtest(get_engine(), league_id, _seasons(seasons))}")


@model_app.command("settle")
def model_settle(league: int | None = typer.Option(None)) -> None:
    """Ergebnis (zugetroffen ja/nein) für Prognosen beendeter Spiele eintragen."""
    from quotenfabrik.analytics.service import settle_predictions

    for league_id in _leagues(league):
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
        result = run_odds_backtest(get_engine(), league_id, validation_until, method, report)
        typer.echo(f"Liga {league_id}: {result}")
    if report:
        typer.echo(f"Bericht: {report}")


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
) -> None:
    """Seed in eine leere Datenbank einspielen (statt Import über die APIs)."""
    from quotenfabrik.seed import SEED_FILE, database_is_empty, drop_schemas, import_seed

    if not database_is_empty():
        if not force:
            typer.secho(
                "Datenbank enthält bereits Daten. Mit --force werden raw/core/analytics gelöscht.", fg="red"
            )
            raise typer.Exit(1)
        drop_schemas()
    import_seed(SEED_FILE)
    typer.echo("Seed eingespielt und Schema auf aktuellen Stand gesetzt (alembic stamp head).")


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
