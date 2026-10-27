"""Tippschein: six fixed decisions per fixture, always the selection the model considers more likely.

Winner (home / draw / away), goals over 1.5, goals over 2.5, both teams score, goal in the 1st half and goal
in the 2nd half (each yes / no). Evaluated retrospectively: hit rate against the model's expectation, a naive
reference (always the outcome that was most frequent in the league's previous seasons), calibration by
confidence, number of correct decisions per fixture and the result at Betano's last price before kickoff.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Decision:
    key: str
    label: str
    market: str
    line: float | None
    options: tuple[tuple[str, str], ...]  # (selection, label)


DECISIONS = (
    Decision("winner", "Sieger", "1x2", None, (("H", "Heim"), ("D", "Unentschieden"), ("A", "Gast"))),
    Decision("o15", "Über 1,5 Tore", "ou_ft", 1.5, (("over", "Ja"), ("under", "Nein"))),
    Decision("o25", "Über 2,5 Tore", "ou_ft", 2.5, (("over", "Ja"), ("under", "Nein"))),
    Decision("btts", "Beide treffen", "btts", None, (("yes", "Ja"), ("no", "Nein"))),
    Decision("goal_1h", "Tor in der 1. Halbzeit", "ou_1h", 0.5, (("over", "Ja"), ("under", "Nein"))),
    Decision("goal_2h", "Tor in der 2. Halbzeit", "ou_2h", 0.5, (("over", "Ja"), ("under", "Nein"))),
)
BY_KEY = {d.key: d for d in DECISIONS}
CONFIDENCE_BINS = [0.0, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.0]


def _key_of(market: str, line) -> str | None:
    line = None if line is None or pd.isna(line) else round(float(line), 2)
    for d in DECISIONS:
        if d.market == market and d.line == line:
            return d.key
    return None


def decide(preds: pd.DataFrame) -> pd.DataFrame:
    """``preds``: fixture_id, market, selection, line, probability (+ outcome, any extra columns) of the
    chosen run. Returns one row per fixture and decision with the more likely selection (``decision``,
    ``pick``, ``pick_label``, ``probability``, ``hit`` if settled)."""
    p = preds.copy()
    p["decision"] = [_key_of(m, ln) for m, ln in zip(p["market"], p["line"], strict=True)]
    p = p[p["decision"].notna()]
    p = p[[s in dict(BY_KEY[k].options) for k, s in zip(p["decision"], p["selection"], strict=True)]]
    if p.empty:
        return p.assign(pick=[], pick_label=[], hit=[])
    best = p.loc[p.groupby(["fixture_id", "decision"])["probability"].idxmax()].copy()
    best["pick"] = best["selection"]
    best["pick_label"] = [
        dict(BY_KEY[k].options)[s] for k, s in zip(best["decision"], best["selection"], strict=True)
    ]
    if "outcome" in p:
        best["hit"] = best["outcome"].map(lambda v: None if pd.isna(v) else bool(v))
        won = p[p["outcome"].fillna(False).astype(bool)]
        actual = won.drop_duplicates(["fixture_id", "decision"]).set_index(["fixture_id", "decision"])[
            "selection"
        ]
        best["actual"] = [
            actual.get((f, k)) for f, k in zip(best["fixture_id"], best["decision"], strict=True)
        ]
    order = {d.key: i for i, d in enumerate(DECISIONS)}
    best["order"] = best["decision"].map(order)
    return best.sort_values(["fixture_id", "order"]).drop(columns="order").reset_index(drop=True)


def _rate(rows: pd.DataFrame) -> dict:
    settled = rows.dropna(subset=["hit"])
    hit = settled["hit"].astype(bool)
    return {
        "n": int(len(settled)),
        "hit_rate": float(hit.mean()) if len(settled) else None,
        "expected": float(settled["probability"].mean()) if len(settled) else None,
    }


def _betano(rows: pd.DataFrame) -> dict | None:
    """Result of 1 unit on every decision at Betano's last price before kickoff (settled, with price)."""
    if "betano" not in rows:
        return None
    b = rows.dropna(subset=["hit", "betano"])
    if b.empty:
        return None
    hit = b["hit"].astype(bool)
    profit = np.where(hit, b["betano"] - 1, -1.0)
    return {
        "n": int(len(b)),
        "odds": float(b["betano"].mean()),
        "hit_rate": float(hit.mean()),
        "roi": float(profit.mean()),
        "edge": float((b["probability"] * b["betano"] - 1).mean()),
    }


def reference_hits(rows: pd.DataFrame) -> pd.Series:
    """Naive reference per row: always the outcome that was most frequent in the previous seasons of the
    data (walk-forward; first season without reference)."""
    out = pd.Series(np.nan, index=rows.index, dtype=object)
    settled = rows.dropna(subset=["actual"])
    for (season, key), g in settled.groupby(["season", "decision"]):
        before = settled[(settled["season"] < season) & (settled["decision"] == key)]
        if before.empty:
            continue
        most = before["actual"].value_counts().idxmax()
        out.loc[g.index] = g["actual"] == most
    return out


def evaluate(rows: pd.DataFrame) -> dict:
    """Hit rates per decision (overall, per season, by confidence) against the model's expectation and the
    naive reference, and the number of correct decisions per fixture."""
    settled = rows.dropna(subset=["hit"]).copy()
    if "actual" in settled and "season" in settled:
        settled["reference"] = reference_hits(settled)
    out_decisions = []
    for d in DECISIONS:
        g = settled[settled["decision"] == d.key]
        entry = {"key": d.key, "label": d.label, **_rate(g)}
        entry["picked"] = {lbl: int((g["pick"] == sel).sum()) for sel, lbl in d.options}
        if "reference" in g:
            ref = g.dropna(subset=["reference"])
            entry["reference"] = (
                None
                if ref.empty
                else {
                    "n": int(len(ref)),
                    "hit_rate": float(ref["reference"].astype(bool).mean()),
                    "model": float(ref["hit"].astype(bool).mean()),
                }
            )
        entry["betano"] = _betano(g)
        cut = pd.cut(g["probability"], CONFIDENCE_BINS, include_lowest=True)
        entry["confidence"] = [
            {"bin": f"{b.left * 100:.0f}–{b.right * 100:.0f} %", **_rate(x)}
            for b, x in g.groupby(cut, observed=True)
            if len(x) >= 10
        ]
        out_decisions.append(entry)
    per_fixture = settled.groupby("fixture_id")["hit"].agg(["sum", "size"])
    full = per_fixture[per_fixture["size"] == len(DECISIONS)]
    distribution = (
        {str(k): float((full["sum"] == k).mean()) for k in range(len(DECISIONS) + 1)} if len(full) else {}
    )
    seasons = []
    if "season" in settled:
        for season, g in settled.groupby("season"):
            by_key = {d.key: _rate(g[g["decision"] == d.key])["hit_rate"] for d in DECISIONS}
            seasons.append({"season": int(season), **_rate(g), **by_key})
    return {
        "fixtures": int(settled["fixture_id"].nunique()),
        "total": _rate(settled),
        "decisions": out_decisions,
        "correct_per_fixture": distribution,
        "mean_correct": float(full["sum"].mean()) if len(full) else None,
        "seasons": seasons,
        "betano": _betano(settled),
    }
