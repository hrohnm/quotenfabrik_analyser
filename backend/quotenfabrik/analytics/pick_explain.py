"""Why a pick was chosen and why the model considers it likely – short German sentences for the hover card.

Rule-based from data the pick already carries (profile window, rank, league base rate, supporting patterns,
Betano / Pinnacle prices) plus the model's expected goals and 1X2 probabilities of the fixture and the past
hit rate of the same pick type. Uses no information from after the forecast.
"""

import math
from dataclasses import dataclass

GOAL_MARKETS = ("ou_", "btts", "clean_sheet")
TRACK_MIN_N = 30  # show the track record only with enough settled picks


@dataclass
class FixtureContext:
    home: str
    away: str
    p_home: float | None = None
    p_draw: float | None = None
    p_away: float | None = None
    xg_home: float | None = None
    xg_away: float | None = None


def team_goals(p_scores: float | None) -> float | None:
    """Expected goals of a team from P(team scores) under a Poisson model: λ = −ln(1 − p)."""
    if p_scores is None or not 0 < p_scores < 1:
        return None
    return -math.log(1 - p_scores)


def _pct(p: float) -> str:
    return f"{p * 100:.0f} %"


def _num(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def _odd(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def explain(
    pick: dict,
    *,
    profile_label: str,
    min_p: float,
    max_p: float,
    group_label: str | None,
    n_picks: int,
    ctx: FixtureContext,
    track: dict | None = None,
) -> dict[str, list[str]]:
    """``{"why": [...], "likely": [...]}`` for one pick (``probability``, ``base_rate``, ``rank``, ``market``,
    ``reasons``, ``betano``, ``edge``, ``pinnacle`` as in the API)."""
    p, base = pick["probability"], pick.get("base_rate")
    group = group_label or pick.get("group")
    why = [
        f"Profil „{profile_label}“: Märkte mit {min_p * 100:.0f}–{_pct(max_p)} Modellwahrscheinlichkeit, "
        "je Marktgruppe höchstens ein Tipp.",
        f"Stärkster Kandidat der Gruppe „{group}“ (Wahrscheinlichkeit plus Abstand zum Ligaschnitt) – "
        f"Rang {pick['rank']} von {n_picks}.",
    ]
    if base is not None:
        d, rate = p - base, _pct(base)
        if d >= 0.10:
            why.append(f"Deutlich über dem Ligaschnitt von {rate} (+{d * 100:.0f} Punkte): "
                       "das Modell sieht in diesem Spiel einen klaren Ausschlag.")  # fmt: skip
        elif d >= 0.03:
            why.append(f"Über dem Ligaschnitt von {rate} (+{d * 100:.0f} Punkte).")
        elif d > -0.03:
            why.append(f"Etwa im Ligaschnitt ({rate}) – gewählt vor allem wegen der hohen "
                       "Grundwahrscheinlichkeit.")  # fmt: skip
        else:
            why.append(f"Unter dem Ligaschnitt von {rate} ({d * 100:.0f} Punkte), im Bereich des "
                       "Profils aber der stärkste verfügbare Tipp.")  # fmt: skip

    likely = []
    market = pick["market"]
    if market.startswith(GOAL_MARKETS) and ctx.xg_home is not None and ctx.xg_away is not None:
        likely.append(f"Das Modell erwartet {_num(ctx.xg_home + ctx.xg_away)} Tore ({ctx.home} "
                      f"{_num(ctx.xg_home)}, {ctx.away} {_num(ctx.xg_away)}).")  # fmt: skip
    elif None not in (ctx.p_home, ctx.p_draw, ctx.p_away):
        likely.append(f"Modell: Sieg {ctx.home} {_pct(ctx.p_home)}, Remis {_pct(ctx.p_draw)}, "
                      f"Sieg {ctx.away} {_pct(ctx.p_away)}.")  # fmt: skip
    likely.append("Grundlage: Teamstärken aus Toren und Schüssen aufs Tor aller bisherigen Spiele "
                  "(Dixon-Coles), nur Daten vor Anpfiff.")  # fmt: skip
    for r in pick.get("reasons") or []:
        value, baseline = r.get("value"), r.get("baseline")
        text = r["label"]
        if value is not None and value <= 1:
            text += f": {_pct(value)}"
            if baseline is not None and baseline <= 1:
                text += f" (Liga {_pct(baseline)})"
        likely.append(f"Pattern: {text}.")
    fair = pick.get("pinnacle")
    if fair is not None:
        agree = "höher als das Modell" if fair > p else "niedriger als das Modell"
        if abs(fair - p) < 0.05:
            agree = "bestätigt das Modell"
        likely.append(f"Der Markt (Pinnacle ohne Marge) sieht {_pct(fair)} – {agree}.")
    if pick.get("betano") is not None and pick.get("edge") is not None:
        edge = pick["edge"]
        likely.append(f"Betano-Quote {_odd(pick['betano'])}: laut Modell "
                      f"{'+' if edge >= 0 else '−'}{_pct(abs(edge))} Erwartungswert.")  # fmt: skip
    if track and track.get("n", 0) >= TRACK_MIN_N:
        hit, expected = _pct(track["hit_rate"]), _pct(track["expected"])
        n = f"{track['n']:,}".replace(",", ".")
        likely.append(f"Bisher traf dieser Tipp-Typ im Profil in {hit} der Fälle "
                      f"({n} abgerechnet, Modell im Schnitt {expected}).")  # fmt: skip
    return {"why": why, "likely": likely}
