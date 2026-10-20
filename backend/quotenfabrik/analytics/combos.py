"""Daily combos ("Tageskombis"): three accumulators per day across all fixtures of the day.

Kinds (one leg per fixture):

* ``tore``           – total goals over (lines 0.5–3.5)
* ``team_tore``      – home or away team goals over (lines 0.5–2.5)
* ``doppelte_chance`` – double chance 1X / X2 / 12

Selection per day:

1. Per kind and fixture the best leg: probability within [min_p, max_p], score = p + lift_weight · (p − base rate)
   (the same idea as the 3 picks per fixture: strong legs where the model deviates from the league average).
2. The three combos pick in turn (round robin, starting kind rotates) their best remaining leg; every fixture
   appears in at most one combo of the day – the combos spread over all fixtures instead of reusing the top
   matches.
3. Legs are added until the estimated odds reach ``target_min``; a leg that would exceed ``target_max`` is
   skipped. Without enough legs there is no combo of that kind on that day.

Odds are estimated from the model: (1 / p) · (1 − margin) per leg (Betano odds for these markets are not
available for all fixtures). The combo wins if all legs win (settled after 90 minutes); legs are on
different fixtures, so the combo probability is the product of the leg probabilities.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

KINDS = {
    "tore": "Tore gesamt – Über",
    "team_tore": "Tore Mannschaft – Über",
    "doppelte_chance": "Doppelte Chance",
}


@dataclass
class ComboSettings:
    target_min: float = 5.0
    target_max: float = 10.0
    min_p: float = 0.55
    max_p: float = 0.85
    margin: float = 0.05  # assumed bookmaker margin per leg (estimated odds)
    min_leg_odds: float = 1.2  # legs with lower odds are skipped
    min_edge: float | None = None  # only legs with Betano odds and p × odds − 1 ≥ min_edge (None = no filter)
    lift_weight: float = 1.0
    max_legs: int = 8


@dataclass
class Combo:
    kind: str
    legs: list[dict] = field(default_factory=list)

    @property
    def odds(self) -> float:
        return float(np.prod([leg["odds"] for leg in self.legs])) if self.legs else 1.0

    @property
    def probability(self) -> float:
        return float(np.prod([leg["probability"] for leg in self.legs])) if self.legs else 1.0

    @property
    def outcome(self) -> bool | None:
        """True if every leg won, False as soon as one leg lost, None while open."""
        outs = [None if leg.get("outcome") is None else bool(leg["outcome"]) for leg in self.legs]
        if any(o is False for o in outs):
            return False
        return True if outs and all(o is True for o in outs) else None


def kind_of(market: str, selection: str, line: float | None) -> str | None:
    if market == "ou_ft" and selection == "over" and line is not None and line <= 3.5:
        return "tore"
    if market in ("ou_home", "ou_away") and selection == "over" and line is not None and line <= 2.5:
        return "team_tore"
    if market == "dc":
        return "doppelte_chance"
    return None


def candidates(preds: pd.DataFrame, s: ComboSettings) -> dict[str, pd.DataFrame]:
    """Eligible legs per kind, ranked by score (several lines per fixture possible).

    preds: fixture_id, market, selection, line, probability, base_rate (NaN allowed) [, outcome, ...].
    """
    if preds.empty:
        return {k: preds for k in KINDS}
    df = preds.copy()
    df["kind"] = [kind_of(m, sel, None if pd.isna(ln) else float(ln))
                  for m, sel, ln in zip(df["market"], df["selection"], df["line"], strict=True)]  # fmt: skip
    df = df[df["kind"].notna() & df["probability"].between(s.min_p, s.max_p)]
    base = df["base_rate"].astype(float).fillna(df["probability"])
    df["score"] = df["probability"] + s.lift_weight * (df["probability"] - base)
    estimate = (1.0 / df["probability"]) * (1.0 - s.margin)
    real = df["betano"].notna() if "betano" in df else pd.Series(False, index=df.index)
    df["odds"] = df["betano"].where(real, estimate) if "betano" in df else estimate
    df["odds_source"] = np.where(real, "betano", "geschätzt")
    df["edge"] = (df["probability"] * df["odds"] - 1).where(real)
    if s.min_edge is not None:
        df = df[df["edge"] >= s.min_edge]
    df = df[df["odds"] >= s.min_leg_odds]
    out = {}
    for kind in KINDS:
        part = df[df["kind"] == kind].sort_values(["score", "probability"], ascending=False)
        out[kind] = part.reset_index(drop=True)  # all legs; the first one per fixture is its best
    return out


def build_day(preds: pd.DataFrame, s: ComboSettings, rotation: int = 0) -> list[Combo]:
    """The combos of one day (only kinds that reach ``target_min``). ``rotation`` shifts the starting kind.

    The kinds pick in turn the best-scoring leg; a fixture not yet used by another combo of the day is preferred,
    a used one is only taken when no unused candidate fits (a fixture never appears twice in the same combo).
    A leg is skipped when the target could no longer be reached with the remaining places (then e.g. Über 2,5
    instead of Über 1,5 of the same fixture).
    """
    if preds.empty:
        return []
    cands = candidates(preds, s)
    order = list(KINDS)
    order = order[rotation % len(order) :] + order[: rotation % len(order)]
    combos = {k: Combo(k) for k in order}
    used: set[int] = set()  # fixtures in any combo of the day
    done: set[str] = set()

    def next_leg(kind: str):
        combo, ranked = combos[kind], cands[kind]
        own = {leg["fixture_id"] for leg in combo.legs}
        fits = ranked[~ranked["fixture_id"].isin(own) & (combo.odds * ranked["odds"] <= s.target_max)]
        if fits.empty:
            return None
        best = fits.groupby("fixture_id")["odds"].max().sort_values(ascending=False)
        slots = s.max_legs - len(combo.legs) - 1  # free places after this leg

        def reachable(leg) -> bool:
            # can the target still be reached with the highest odds of the other fixtures?
            rest = best.drop(leg["fixture_id"]).head(slots)
            return combo.odds * leg["odds"] * float(rest.prod()) >= s.target_min

        fresh = fits[~fits["fixture_id"].isin(used)]
        for pool in (fresh, fits):
            for _, leg in pool.iterrows():
                if reachable(leg):
                    return leg
        return fits.iloc[0]

    while len(done) < len(order):
        for kind in order:
            if kind in done:
                continue
            leg = next_leg(kind)
            if leg is None:
                done.add(kind)
                continue
            combo = combos[kind]
            used.add(int(leg["fixture_id"]))
            combo.legs.append(
                {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in leg.items()}
            )
            if combo.odds >= s.target_min or len(combo.legs) >= s.max_legs:
                done.add(kind)
    return [c for c in combos.values() if c.odds >= s.target_min]


# --------------------------------------------------------------------------- backtest


def backtest(preds: pd.DataFrame, s: ComboSettings) -> pd.DataFrame:
    """One row per combo built on each day of ``preds`` (needs ``day`` and ``outcome`` columns)."""
    rows = []
    for day, part in sorted(preds.groupby("day"), key=lambda x: x[0]):
        for c in build_day(part, s, rotation=pd.Timestamp(day).toordinal()):  # same rotation as live
            outcome = c.outcome
            if outcome is None:
                continue
            rows.append({"day": day, "season": int(part["season"].iloc[0]), "kind": c.kind, "legs": len(c.legs),
                         "odds": c.odds, "probability": c.probability, "won": bool(outcome),
                         "leg_hits": sum(bool(leg["outcome"]) for leg in c.legs),
                         "real": all(leg.get("odds_source") == "betano" for leg in c.legs)})  # fmt: skip
    return pd.DataFrame(rows)


def summary(results: pd.DataFrame) -> pd.DataFrame:
    """Hit rate, expected hit rate (model) and return per kind (stake 1 at the estimated odds)."""
    if results.empty:
        return pd.DataFrame()
    g = results.groupby("kind")
    out = pd.DataFrame({
        "n": g.size(), "hit_rate": g["won"].mean(), "expected": g["probability"].mean(),
        "odds": g["odds"].mean(), "legs": g["legs"].mean(),
        "roi": g.apply(lambda d: float((d["won"] * d["odds"]).sum() / len(d) - 1), include_groups=False),
    })  # fmt: skip
    return out.reindex([k for k in KINDS if k in out.index])


# --------------------------------------------------------------------------- data

_PREDICTIONS_SQL = """
    select p.fixture_id, p.market, p.selection, p.line::float as line, p.probability, p.outcome,
           f.league_id, f.season, f.kickoff_utc as kickoff,
           (f.kickoff_utc at time zone 'Europe/Berlin')::date as day
    from analytics.predictions p
    join analytics.model_runs r on r.id = p.model_run_id
    join core.fixtures f on f.id = p.fixture_id
    where r.kind = 'backtest' and r.league_id = any(:leagues)
      and p.market in ('ou_ft', 'ou_home', 'ou_away', 'dc') and p.selection in ('over', '1X', 'X2', '12')
"""


def with_base_rates(engine, preds: pd.DataFrame) -> pd.DataFrame:
    """Adds ``base_rate`` (league frequency of the selection in the 3 years before the matchday, no leakage)."""
    from quotenfabrik.analytics.data import load_matches
    from quotenfabrik.analytics.picks import base_rates

    parts = []
    for league_id, part in preds.groupby("league_id"):
        matches = load_matches(engine, int(league_id))
        fixtures = matches[matches["fixture_id"].isin(part["fixture_id"].unique())][
            ["fixture_id", "season", "matchday", "kickoff"]
        ].copy()
        if fixtures["matchday"].isna().all():  # cups: group by week
            iso = fixtures["kickoff"].dt.isocalendar()
            fixtures["matchday"] = iso["year"].astype(int) * 100 + iso["week"].astype(int)
        parts.append(part.merge(base_rates(matches, fixtures), on=["fixture_id", "market", "selection", "line"],
                                how="left"))  # fmt: skip
    return pd.concat(parts, ignore_index=True) if parts else preds.assign(base_rate=np.nan)


def load_backtest(engine, league_ids: list[int]) -> pd.DataFrame:
    """Walk-forward (backtest) predictions of the combo markets with outcomes and base rates."""
    from sqlalchemy import text

    preds = pd.read_sql(text(_PREDICTIONS_SQL), engine, params={"leagues": league_ids})
    preds = preds[preds["outcome"].notna()]
    return with_betano(engine, with_base_rates(engine, preds))


COMBO_MARKET_TYPES = ["totals", "teamtotals-team1", "teamtotals-team2", "doublechance", "1x2"]


def with_betano(engine, preds: pd.DataFrame) -> pd.DataFrame:
    """Adds ``betano`` (last Betano odds before kickoff, NaN without OddsPapi history) and ``fair`` (Pinnacle)."""
    from quotenfabrik.analytics.bookmaker_odds import KEY, odds_table

    table = odds_table(engine, sorted(preds["fixture_id"].unique()), COMBO_MARKET_TYPES)
    preds = preds.drop(columns=["betano", "fair", "betano_at"], errors="ignore").astype({"line": float})
    return preds.merge(table[[*KEY, "betano", "fair", "betano_at"]], on=KEY, how="left")


# --------------------------------------------------------------------------- report

VARIANTS = {
    "sicherere Tipps (65–90 %)": {"min_p": 0.65, "max_p": 0.90},
    "Standard (55–85 %)": {},
    "Standard ohne Mindestquote je Tipp": {"min_leg_odds": 1.0},
    "riskantere Tipps (45–75 %)": {"min_p": 0.45, "max_p": 0.75},
}


def _pct(x: float) -> str:
    return f"{x * 100:.1f} %".replace(".", ",")


def _num(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def _real_odds_section(preds: pd.DataFrame, base: ComboSettings, std: pd.DataFrame) -> list[str]:
    """Combos whose legs all have real Betano closing odds, plus value-only variants (Betano odds × p ≥ 1 + edge)."""
    from dataclasses import replace

    if "betano" not in preds or preds["betano"].isna().all():
        return [
            "",
            "## Mit echten Betano-Quoten",
            "",
            "Noch keine Spiele mit Betano-Quotenverlauf (OddsPapi).",
        ]
    days = preds.loc[preds["betano"].notna(), "day"].nunique()
    out = ["", "## Mit echten Betano-Quoten", "",
           f"Spieltage mit Betano-Verlauf (OddsPapi, seit Januar 2026): {days}. Quote = letzte Betano-Quote vor "
           "Anpfiff. „Nur Value-Tipps“ nimmt nur Tipps, bei denen Modell-Wahrscheinlichkeit × Betano-Quote über "
           "1 + Mindestvorteil liegt.", "",
           "| Variante | Kombi | Kombis | getroffen | Modell erwartet | Ø Quote | Ø Tipps | Rendite |",
           "|---|---|---:|---:|---:|---:|---:|---:|"]  # fmt: skip
    variants = {"Standard, alle Tipps mit Betano-Quote": std[std["real"]] if not std.empty else std}
    for edge in (0.0, 0.05):
        variants[f"nur Value-Tipps (Vorteil ≥ {edge * 100:.0f} %)"] = backtest(
            preds, replace(base, min_edge=edge)
        )
    for name, res in variants.items():
        for kind, r in summary(res).iterrows():
            out.append(f"| {name} | {KINDS[kind]} | {int(r['n'])} | {_pct(r['hit_rate'])} | {_pct(r['expected'])} | "
                       f"{_num(r['odds'])} | {_num(r['legs'], 1)} | {_pct(r['roi'])} |")  # fmt: skip
    out += ["", "Wenige Kombis: die Rendite schwankt hier stark und ist noch kein Beleg für einen Vorteil."]
    return out


def report(preds: pd.DataFrame, base: ComboSettings, league_names: list[str]) -> str:
    """Markdown report: hit rates of the daily combos on the walk-forward predictions, three variants."""
    from dataclasses import replace
    from datetime import UTC, datetime

    results = {name: backtest(preds, replace(base, **change)) for name, change in VARIANTS.items()}
    std = results["Standard (55–85 %)"]
    days = preds["day"].nunique()
    out = [
        "# 16 – Tageskombis: Erfolgschance im Backtest",
        "",
        f"Automatisch erzeugt von `qf combos report` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC. Wettbewerbe: "
        f"{', '.join(league_names)}; {days} Spieltage mit rückwirkenden Prognosen (Walk-Forward, kein Data Leakage).",
        "",
        "**Regeln:** Pro Tag bis zu drei Kombis – Tore gesamt Über, Tore einer Mannschaft Über, Doppelte Chance – über "
        "alle Spiele des Tages. Je Spiel und Art zählt der stärkste Tipp (Wahrscheinlichkeit plus Abweichung vom "
        "Ligaschnitt); die Kombis wählen abwechselnd, Spiele ohne Kombi werden bevorzugt. Aufgefüllt wird bis zur "
        f"Zielquote {_num(base.target_min, 0)}–{_num(base.target_max, 0)}. Die Quote je Tipp ist geschätzt: "
        f"faire Quote × (1 − {_pct(base.margin)} Marge); Tipps unter {_num(base.min_leg_odds, 2)} werden ausgelassen. Gewonnen ist eine Kombi nur, wenn alle Tipps sitzen "
        "(nach 90 Minuten).",
        "",
        "**Wichtig:** Auch bei perfekten Wahrscheinlichkeiten zahlt jeder Tipp die Buchmacher-Marge. Erwartete Rendite "
        "einer Kombi aus n Tipps ohne eigenen Vorteil: (1 − Marge)ⁿ − 1, bei 5 % Marge und 7 Tipps also ≈ −30 %. "
        "Gewinn entsteht nur, wenn das Modell die Wahrscheinlichkeiten besser kennt als der Buchmacher.",
        "",
        "## Ergebnis je Variante",
        "",
        "| Variante | Kombi | Kombis | getroffen | Modell erwartet | Ø Quote | Ø Tipps | Rendite |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, res in results.items():
        for kind, r in summary(res).iterrows():
            out.append(f"| {name} | {KINDS[kind]} | {int(r['n'])} | {_pct(r['hit_rate'])} | {_pct(r['expected'])} | "
                       f"{_num(r['odds'])} | {_num(r['legs'], 1)} | {_pct(r['roi'])} |")  # fmt: skip
    out += ["", "Getroffen > erwartet heißt: das Modell war bei diesen Tipps eher zu vorsichtig. Die Rendite ist mit der "
            "geschätzten Quote gerechnet, für Spiele mit OddsPapi-Verlauf (seit Januar 2026) mit der echten "
            "Betano-Schlussquote.", "", "## Standard je Saison", "",
            "| Saison | Kombi | Kombis | getroffen | Modell erwartet | Rendite |", "|---|---|---:|---:|---:|---:|"]  # fmt: skip
    if not std.empty:
        for (season, kind), g in std.groupby(["season", "kind"]):
            roi = float((g["won"] * g["odds"]).sum() / len(g) - 1)
            out.append(f"| {season}/{(season + 1) % 100:02d} | {KINDS[kind]} | {len(g)} | {_pct(g['won'].mean())} | "
                       f"{_pct(g['probability'].mean())} | {_pct(roi)} |")  # fmt: skip
        out += ["", "## Wie knapp war es? (Standard)", "", "| Kombi | alle Tipps richtig | einer daneben | zwei oder mehr daneben |",
                "|---|---:|---:|---:|"]  # fmt: skip
        for kind, g in std.groupby("kind"):
            miss = g["legs"] - g["leg_hits"]
            out.append(f"| {KINDS[kind]} | {_pct((miss == 0).mean())} | {_pct((miss == 1).mean())} | "
                       f"{_pct((miss >= 2).mean())} |")  # fmt: skip
    out += _real_odds_section(preds, base, std)
    out += [
        "",
        "## Bewertung",
        "",
        f"- Tage mit Kombi: {std['day'].nunique() if not std.empty else 0} von {days} – an Tagen mit wenigen Spielen "
        "wird die Zielquote nicht erreicht, dann gibt es keine Kombi.",
        "- Eine Kombi mit Quote 5–10 gewinnt erwartungsgemäß nur in rund 10–20 % der Fälle; längere Serien ohne "
        "Gewinn sind normal. Einsatz pro Kombi daher klein halten.",
        "- Weniger, dafür riskantere Tipps verlieren weniger an Marge; sehr sichere Tipps brauchen viele Beine und "
        "kosten mehr Marge – die Varianten oben zeigen den Effekt.",
        "- Ob sich das Spielen lohnt, entscheidet die echte Betano-Quote: im Wett-Tracking die tatsächliche Quote "
        "eintragen und Rendite gegen die Modell-Erwartung vergleichen.",
        "",
    ]
    return "\n".join(out)
