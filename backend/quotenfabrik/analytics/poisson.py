"""Time-weighted Dixon-Coles / Poisson team-strength model.

log(lambda_home) = mu + home_adv + attack[home] - defence[away]
log(lambda_away) = mu            + attack[away] - defence[home]

Fit: weighted Poisson likelihood with weights exp(-xi * days_ago) and an L2 penalty that pulls team
parameters towards a prior centre (0 for established teams, a promoted-team prior for teams without
recent matches). The Dixon-Coles rho (low-score correction) is fitted afterwards for fixed lambdas.
Targets may be non-integer (e.g. a blend of goals and xG); the Poisson likelihood is then a quasi-likelihood.

Shots (``shots_weight``): the target becomes a blend of goals and a shot-based expectation (shots on target or
all shots of the match × the goals-per-shot rate of the training window). Shots are a steadier signal of a
team's strength than goals (validated in docs/18_spielstil.md and docs/19_schuesse_im_modell.md). The rate
comes from matches before ``as_of`` only; the Dixon-Coles rho is still fitted on the real scores.

Several leagues (joint model): with a ``league_id`` column covering more than one league, every league gets
an attack and a defence level and a team's prior centre is the time-weighted mix of the levels of the leagues
it played in (teams without matches: their current league from ``team_league``). Team parameters then live on
one scale across leagues; the levels are identified by teams that played in more than one league
(promotion/relegation) and by cup matches between leagues. With a single league the model is unchanged.

Cup matches (column ``cup``, e.g. European cups): they enter the likelihood but never define a league level
(a team's level comes from its domestic league). Column ``neutral``: no home advantage (finals). Optionally a
separate home advantage for cup matches (``cup_home_adv``).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.stats import poisson

NEW_TEAM_GAP_DAYS = 400  # no match in the window for this long -> treated as newly promoted


@dataclass
class PoissonParams:
    # Defaults chosen on validation seasons 2018-2021 (see docs/09_modell_evaluation.md)
    xi: float = 0.0015  # time decay per day (half-life ~ 15 months)
    reg: float = 10.0  # L2 penalty strength on team parameters
    window_days: int = 3 * 365
    promoted_attack: float = -0.3
    promoted_defence: float = -0.3
    half_reg: float = 25.0  # stronger penalty for the noisier half-time models
    fit_rho: bool = True
    xg_weight: float = 0.0  # 0 = goals only, 1 = xG only (where available)
    shots_weight: float = 0.0  # 0 = goals only; share of the shot-based expectation in the target
    shots_mode: str = "on_target"  # 'on_target' (shots on target) or 'all' (all shots)
    league_reg: float = 1.0  # weak L2 penalty on league levels (joint model only; anchors their mean at 0)
    cup_home_adv: bool = True  # own home advantage for cup matches (validated in docs/15_europapokal.md)


@dataclass
class FittedPoisson:
    params: PoissonParams
    mu: float
    home_adv: float
    attack: dict[int, float]
    defence: dict[int, float]
    rho: float = 0.0
    new_teams: set[int] = field(default_factory=set)
    league_attack: dict[int, float] = field(default_factory=dict)  # joint model: level per league
    league_defence: dict[int, float] = field(default_factory=dict)
    team_league: dict[int, int] = field(default_factory=dict)
    home_adv_cup: float | None = None  # own home advantage of cup matches (None = same as league matches)

    def team_attack(self, team: int) -> float:
        if team in self.attack:
            return self.attack[team]
        return self.league_attack.get(self.team_league.get(team), 0.0) + self.params.promoted_attack

    def team_defence(self, team: int) -> float:
        if team in self.defence:
            return self.defence[team]
        return self.league_defence.get(self.team_league.get(team), 0.0) + self.params.promoted_defence

    def lambdas(self, home: int, away: int, cup: bool = False, neutral: bool = False) -> tuple[float, float]:
        if neutral:
            adv = 0.0
        elif cup and self.home_adv_cup is not None:
            adv = self.home_adv_cup
        else:
            adv = self.home_adv
        lh = np.exp(self.mu + adv + self.team_attack(home) - self.team_defence(away))
        la = np.exp(self.mu + self.team_attack(away) - self.team_defence(home))
        return float(lh), float(la)


def fit_poisson(
    matches: pd.DataFrame,
    as_of: pd.Timestamp,
    params: PoissonParams,
    home_col: str = "hg",
    away_col: str = "ag",
    current_teams: set[int] | None = None,
    home_xg_col: str | None = None,
    away_xg_col: str | None = None,
    team_league: dict[int, int] | None = None,
) -> FittedPoisson:
    """Fits on finished matches before ``as_of``; ``current_teams`` get parameters even without data.

    ``team_league``: current league per team (joint model; used for teams without matches in the window).
    """
    train = matches[
        matches["finished"]
        & (matches["kickoff"] < as_of)
        & (matches["kickoff"] >= as_of - pd.Timedelta(days=params.window_days))
    ]
    yh = train[home_col].to_numpy(float)
    ya = train[away_col].to_numpy(float)
    if params.xg_weight > 0 and home_xg_col and away_xg_col:
        hx, ax = train[home_xg_col].to_numpy(float), train[away_xg_col].to_numpy(float)
        has = ~np.isnan(hx) & ~np.isnan(ax)
        yh = np.where(has, (1 - params.xg_weight) * yh + params.xg_weight * hx, yh)
        ya = np.where(has, (1 - params.xg_weight) * ya + params.xg_weight * ax, ya)
    days = (as_of - train["kickoff"]).dt.total_seconds().to_numpy() / 86400.0
    w = np.exp(-params.xi * days)
    if params.shots_weight > 0:
        yh, ya = _with_shots(train, yh, ya, w, params, home_col, away_col)

    teams = sorted(set(train["home_id"]) | set(train["away_id"]) | set(current_teams or ()))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = train["home_id"].map(idx).to_numpy()
    ai = train["away_id"].map(idx).to_numpy()
    cup = train["cup"].to_numpy(bool) if "cup" in train.columns else np.zeros(len(train), bool)
    neutral = train["neutral"].to_numpy(bool) if "neutral" in train.columns else np.zeros(len(train), bool)
    h_league = (~cup & ~neutral).astype(float)  # which matches carry which home advantage
    h_cup = (cup & ~neutral).astype(float)
    own_cup_home = params.cup_home_adv and bool(h_cup.any())

    last_seen = pd.concat(
        [train[["home_id", "kickoff"]].rename(columns={"home_id": "t"}),
         train[["away_id", "kickoff"]].rename(columns={"away_id": "t"})]
    ).groupby("t")["kickoff"].max()  # fmt: skip
    new_teams = {
        t for t in teams if t not in last_seen.index or (as_of - last_seen[t]).days > NEW_TEAM_GAP_DAYS
    }
    league_rows = ~cup  # cup matches never define a league level
    mix, leagues = _league_mix(train[league_rows], w[league_rows], teams, idx, new_teams, team_league or {})
    # newcomer prior: teams without recent matches, and (joint model) teams of leagues we have no data for
    # (e.g. cup qualifiers from small countries)
    no_league = mix.sum(axis=1) == 0 if mix.shape[1] else np.zeros(n, bool)
    prior = np.array([t in new_teams for t in teams]) | no_league
    offset_a = np.where(prior, params.promoted_attack, 0.0)
    offset_d = np.where(prior, params.promoted_defence, 0.0)
    k = len(leagues)  # 0 = single league: centres are the fixed offsets (unchanged model)
    m = 3 + 2 * n  # mu, home, home (cup) | attack, defence | league attack, league defence

    def unpack(x):
        return x[0], x[1], x[2], x[3 : 3 + n], x[3 + n : m], x[m : m + k], x[m + k :]

    def objective(x):
        mu, home, home_c, att, dfc, la_, ld_ = unpack(x)
        adv = home * h_league + (home_c if own_cup_home else home) * h_cup
        eta_h = mu + adv + att[hi] - dfc[ai]
        eta_a = mu + att[ai] - dfc[hi]
        lh, la = np.exp(eta_h), np.exp(eta_a)
        nll = np.sum(w * (lh - yh * eta_h)) + np.sum(w * (la - ya * eta_a))
        ra = att - offset_a - (mix @ la_ if k else 0.0)
        rd = dfc - offset_d - (mix @ ld_ if k else 0.0)
        nll += 0.5 * params.reg * (ra @ ra + rd @ rd) + 0.5 * params.league_reg * (la_ @ la_ + ld_ @ ld_)
        rh, rah = w * (lh - yh), w * (la - ya)
        g_att = np.bincount(hi, rh, n) + np.bincount(ai, rah, n) + params.reg * ra
        g_def = -np.bincount(ai, rh, n) - np.bincount(hi, rah, n) + params.reg * rd
        g_la = -params.reg * (mix.T @ ra) + params.league_reg * la_ if k else np.zeros(0)
        g_ld = -params.reg * (mix.T @ rd) + params.league_reg * ld_ if k else np.zeros(0)
        g_home = rh @ h_league + (0.0 if own_cup_home else rh @ h_cup)
        g_home_c = rh @ h_cup if own_cup_home else 0.0
        grad = np.concatenate([[rh.sum() + rah.sum(), g_home, g_home_c], g_att, g_def, g_la, g_ld])
        return nll, grad

    x0 = np.zeros(m + 2 * k)
    total_w = w.sum() if len(w) else 1.0
    if len(w):
        x0[0] = np.log(max((w @ (yh + ya)) / (2 * total_w), 0.1))
    x0[3 : 3 + n], x0[3 + n : m] = offset_a, offset_d
    res = minimize(objective, x0, jac=True, method="L-BFGS-B")
    mu, home, home_c, att, dfc, la_, ld_ = unpack(res.x)
    fitted = FittedPoisson(
        params=params,
        mu=float(mu),
        home_adv=float(home),
        attack={t: float(att[i]) for t, i in idx.items()},
        defence={t: float(dfc[i]) for t, i in idx.items()},
        new_teams=new_teams,
        league_attack={lg: float(la_[j]) for j, lg in enumerate(leagues)},
        league_defence={lg: float(ld_[j]) for j, lg in enumerate(leagues)},
        team_league=dict(team_league or {}),
        home_adv_cup=float(home_c) if own_cup_home else None,
    )
    if params.fit_rho and len(train):
        fitted.rho = _fit_rho(fitted, train, w, home_col, away_col)
    return fitted


SHOT_COLUMNS = {"on_target": ("hst", "ast"), "all": ("hs", "as_")}


def _with_shots(
    train: pd.DataFrame,
    yh: np.ndarray,
    ya: np.ndarray,
    w: np.ndarray,
    params: PoissonParams,
    hc: str,
    ac: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Blend of the targets with shots × goals-per-shot rate of the window (matches without shot data keep
    their targets)."""
    sh_col, sa_col = SHOT_COLUMNS[params.shots_mode]
    if sh_col not in train.columns or sa_col not in train.columns:
        return yh, ya
    sh, sa = train[sh_col].to_numpy(float), train[sa_col].to_numpy(float)
    has = ~np.isnan(sh) & ~np.isnan(sa)
    if not has.any():
        return yh, ya
    goals = train[hc].to_numpy(float) + train[ac].to_numpy(float)
    rate = float(w[has] @ goals[has]) / max(float(w[has] @ (sh[has] + sa[has])), 1e-9)
    s = params.shots_weight
    yh = np.where(has, (1 - s) * yh + s * rate * np.nan_to_num(sh), yh)
    ya = np.where(has, (1 - s) * ya + s * rate * np.nan_to_num(sa), ya)
    return yh, ya


def _league_mix(
    train: pd.DataFrame,
    w: np.ndarray,
    teams: list[int],
    idx: dict[int, int],
    new_teams: set[int],
    team_league: dict[int, int],
) -> tuple[np.ndarray, list[int]]:
    """(n_teams x n_leagues) weights of the league levels in each team's prior centre, and the leagues.

    Teams with matches: time-weighted share of their matches per league. Teams without recent matches
    (``new_teams``): their current league. Empty when the data covers fewer than two leagues.
    """
    if "league_id" not in train.columns:
        return np.zeros((len(teams), 0)), []
    leagues = sorted(set(train["league_id"]) | {lg for t, lg in team_league.items() if t in idx})
    if len(leagues) < 2:
        return np.zeros((len(teams), 0)), []
    col = {lg: j for j, lg in enumerate(leagues)}
    mix = np.zeros((len(teams), len(leagues)))
    lj = train["league_id"].map(col).to_numpy()
    for side in ("home_id", "away_id"):
        np.add.at(mix, (train[side].map(idx).to_numpy(), lj), w)
    for t in teams:
        row = mix[idx[t]]
        if t in new_teams or row.sum() <= 0:
            row[:] = 0.0
            if t in team_league:
                row[col[team_league[t]]] = 1.0
        else:
            row /= row.sum()
    return mix, leagues


def _dc_tau(x: np.ndarray, y: np.ndarray, lh: np.ndarray, la: np.ndarray, rho: float) -> np.ndarray:
    tau = np.ones_like(lh)
    tau = np.where((x == 0) & (y == 0), 1 - lh * la * rho, tau)
    tau = np.where((x == 0) & (y == 1), 1 + lh * rho, tau)
    tau = np.where((x == 1) & (y == 0), 1 + la * rho, tau)
    tau = np.where((x == 1) & (y == 1), 1 - rho, tau)
    return tau


def _fit_rho(model: FittedPoisson, train: pd.DataFrame, w: np.ndarray, hc: str, ac: str) -> float:
    cup = train["cup"] if "cup" in train.columns else pd.Series(False, index=train.index)
    neutral = train["neutral"] if "neutral" in train.columns else pd.Series(False, index=train.index)
    lam = np.array([
        model.lambdas(h, a, bool(c), bool(nt))
        for h, a, c, nt in zip(train["home_id"], train["away_id"], cup, neutral, strict=True)
    ])  # fmt: skip
    x, y = train[hc].to_numpy(float), train[ac].to_numpy(float)
    integer = (x == np.round(x)) & (y == np.round(y))
    x, y, lh, la, w = x[integer], y[integer], lam[integer, 0], lam[integer, 1], w[integer]

    def nll(rho):
        tau = _dc_tau(x, y, lh, la, rho)
        return -np.sum(w * np.log(np.clip(tau, 1e-10, None)))

    return float(minimize_scalar(nll, bounds=(-0.25, 0.25), method="bounded").x)


def score_matrix(lh: float, la: float, rho: float = 0.0, max_goals: int = 10) -> np.ndarray:
    """P(home = i, away = j) for i, j in 0..max_goals, Dixon-Coles corrected and renormalised."""
    goals = np.arange(max_goals + 1)
    m = np.outer(poisson.pmf(goals, lh), poisson.pmf(goals, la))
    if rho:
        m[0, 0] *= 1 - lh * la * rho
        m[0, 1] *= 1 + lh * rho
        m[1, 0] *= 1 + la * rho
        m[1, 1] *= 1 - rho
    m = np.clip(m, 0, None)
    return m / m.sum()
