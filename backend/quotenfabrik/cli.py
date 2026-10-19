"""Command line interface ``qf``."""

import logging
from datetime import UTC, datetime

import httpx
import typer
from sqlalchemy.orm import Session

from quotenfabrik.config import get_settings
from quotenfabrik.db import get_engine
from quotenfabrik.ingest import api_football, football_data, odds, quality, rebuild, team_mapping
from quotenfabrik.ingest.db_utils import raw_response_saver
from quotenfabrik.sources.api_football import ApiFootballClient, QuotaExhausted

app = typer.Typer(help="Quotenfabrik Analyser", no_args_is_help=True)
ingest_app = typer.Typer(help="Daten importieren", no_args_is_help=True)
odds_app = typer.Typer(help="Quoten-Archiv", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")
app.add_typer(odds_app, name="odds")


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
