"""Group 5: goalscorer model.

lambda_player = rate_per_90 * expected_minutes / 90 * (lambda_team_match / team_avg_goals)
P(anytime)    = 1 - exp(-lambda_player)
P(first)      = lambda_player / (lambda_home + lambda_away) * (1 - exp(-(lambda_home + lambda_away)))

* rate_per_90: time-weighted goals per 90 minutes, shrunk to the position mean (empirical Bayes)
* expected_minutes: from the lineup (starter / bench) once known, otherwise from the start probability
* team ratio: adjusts the player's rate to the strength of this match (from the team model)
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quotenfabrik.analytics.markets.base import MarketProbability

GROUP = "scorers"


@dataclass
class ScorerParams:
    # Defaults chosen on validation seasons 2020-2021 (see docs/09_modell_evaluation.md)
    xi: float = 0.0015
    window_days: int = 3 * 365
    shrink_90s: float = 15.0  # prior weight in 90-minute units
    start_minutes_prior: float = 78.0
    bench_minutes_prior: float = 11.0
    minutes_shrink: float = 3.0
    recent_matches_for_start_prob: int = 5
    team_ratio_power: float = 0.6  # 1 = full adjustment to the match's expected team goals


@dataclass
class PlayerRate:
    player_id: int
    team_id: int
    name: str
    position: str | None
    rate90: float
    start_minutes: float
    bench_minutes: float
    start_prob: float


class ScorerModel:
    def __init__(self, params: ScorerParams | None = None) -> None:
        self.params = params or ScorerParams()
        self.players: dict[int, PlayerRate] = {}
        self.position_rate90: dict[str, float] = {}
        self.team_avg_goals: dict[int, float] = {}

    def fit(self, player_matches: pd.DataFrame, matches: pd.DataFrame, as_of: pd.Timestamp) -> "ScorerModel":
        p = self.params
        hist = player_matches[
            (player_matches["kickoff"] < as_of)
            & (player_matches["kickoff"] >= as_of - pd.Timedelta(days=p.window_days))
        ].copy()
        hist["w"] = np.exp(-p.xi * (as_of - hist["kickoff"]).dt.total_seconds() / 86400.0)
        hist["wg"] = hist["w"] * hist["goals"]
        hist["w90"] = hist["w"] * hist["minutes"] / 90.0

        pos = hist[hist["position"].isin(["G", "D", "M", "F"])].groupby("position")[["wg", "w90"]].sum()
        self.position_rate90 = (pos["wg"] / pos["w90"].clip(lower=1e-9)).to_dict()
        league_rate = float(hist["wg"].sum() / max(hist["w90"].sum(), 1e-9))

        # latest team and position per player
        latest = hist.sort_values("kickoff").groupby("player_id").tail(1).set_index("player_id")
        agg = hist.groupby("player_id")[["wg", "w90"]].sum()
        starters = hist[hist["is_starter"] == True]  # noqa: E712
        bench = hist[hist["is_starter"] == False]  # noqa: E712
        start_min = starters.groupby("player_id").apply(_weighted_minutes, include_groups=False)
        bench_min = bench.groupby("player_id").apply(_weighted_minutes, include_groups=False)

        recent = hist.sort_values("kickoff").groupby("player_id").tail(p.recent_matches_for_start_prob)
        start_prob = recent.groupby("player_id")["is_starter"].mean()

        self.players = {}
        for pid, row in agg.iterrows():
            info = latest.loc[pid]
            prior = self.position_rate90.get(info["position"], league_rate)
            rate = (row["wg"] + p.shrink_90s * prior) / (row["w90"] + p.shrink_90s)
            sm = start_min.get(pid, (0.0, 0.0))
            bm = bench_min.get(pid, (0.0, 0.0))
            self.players[pid] = PlayerRate(
                player_id=int(pid),
                team_id=int(info["team_id"]),
                name=str(info["name"]),
                position=info["position"],
                rate90=float(rate),
                start_minutes=(sm[0] + p.minutes_shrink * p.start_minutes_prior) / (sm[1] + p.minutes_shrink),
                bench_minutes=(bm[0] + p.minutes_shrink * p.bench_minutes_prior) / (bm[1] + p.minutes_shrink),
                start_prob=float(start_prob.get(pid, 0.0) or 0.0),
            )

        played = matches[matches["finished"] & (matches["kickoff"] < as_of)
                         & (matches["kickoff"] >= as_of - pd.Timedelta(days=p.window_days))]  # fmt: skip
        w = np.exp(-p.xi * (as_of - played["kickoff"]).dt.total_seconds() / 86400.0)
        goals = pd.concat(
            [pd.DataFrame({"t": played["home_id"], "g": played["hg"], "w": w}),
             pd.DataFrame({"t": played["away_id"], "g": played["ag"], "w": w})]
        )  # fmt: skip
        goals["wg"] = goals["g"] * goals["w"]
        tg = goals.groupby("t")[["wg", "w"]].sum()
        league_avg = float(goals["wg"].sum() / max(goals["w"].sum(), 1e-9))
        # shrunk towards the league average so teams with few matches get a stable reference
        self.team_avg_goals = ((tg["wg"] + 3 * league_avg) / (tg["w"] + 3)).to_dict()
        return self

    def expected_minutes(self, player: PlayerRate, is_starter: bool | None) -> float:
        if is_starter is True:
            return player.start_minutes
        if is_starter is False:
            return player.bench_minutes
        return player.start_prob * player.start_minutes + (1 - player.start_prob) * player.bench_minutes

    def player_lambda(
        self, player_id: int, team_id: int, team_lambda: float, is_starter: bool | None
    ) -> float:
        player = self.players.get(player_id)
        if player is None:
            return 0.0
        reference = self.team_avg_goals.get(team_id) or team_lambda
        ratio = (team_lambda / reference) ** self.params.team_ratio_power if reference else 1.0
        return player.rate90 * self.expected_minutes(player, is_starter) / 90.0 * ratio

    def probabilities(
        self, squad: pd.DataFrame, lh: float, la: float, home_id: int
    ) -> list[MarketProbability]:
        """``squad`` columns: player_id, team_id, is_starter (True/False/None)."""
        total = lh + la
        p_any_goal = 1 - np.exp(-total)
        out = []
        for row in squad.itertuples(index=False):
            team_lambda = lh if row.team_id == home_id else la
            lam = self.player_lambda(row.player_id, row.team_id, team_lambda, row.is_starter)
            out.append(MarketProbability("scorer_anytime", str(row.player_id), None, float(1 - np.exp(-lam))))
            first = lam / total * p_any_goal if total else 0.0
            out.append(MarketProbability("scorer_first", str(row.player_id), None, float(first)))
        return out


def _weighted_minutes(df: pd.DataFrame) -> tuple[float, float]:
    return float((df["w"] * df["minutes"]).sum()), float(df["w"].sum())
