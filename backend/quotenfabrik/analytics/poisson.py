"""Time-weighted Dixon-Coles / Poisson team-strength model.

log(lambda_home) = mu + home_adv + attack[home] - defence[away]
log(lambda_away) = mu            + attack[away] - defence[home]

Fit: weighted Poisson likelihood with weights exp(-xi * days_ago) and an L2 penalty that pulls team
parameters towards a prior centre (0 for established teams, a promoted-team prior for teams without
recent matches). The Dixon-Coles rho (low-score correction) is fitted afterwards for fixed lambdas.
Targets may be non-integer (e.g. a blend of goals and xG); the Poisson likelihood is then a quasi-likelihood.
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


@dataclass
class FittedPoisson:
    params: PoissonParams
    mu: float
    home_adv: float
    attack: dict[int, float]
    defence: dict[int, float]
    rho: float = 0.0
    new_teams: set[int] = field(default_factory=set)

    def team_attack(self, team: int) -> float:
        return self.attack.get(team, self.params.promoted_attack)

    def team_defence(self, team: int) -> float:
        return self.defence.get(team, self.params.promoted_defence)

    def lambdas(self, home: int, away: int) -> tuple[float, float]:
        lh = np.exp(self.mu + self.home_adv + self.team_attack(home) - self.team_defence(away))
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
) -> FittedPoisson:
    """Fits on finished matches before ``as_of``; ``current_teams`` get parameters even without data."""
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

    teams = sorted(set(train["home_id"]) | set(train["away_id"]) | set(current_teams or ()))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = train["home_id"].map(idx).to_numpy()
    ai = train["away_id"].map(idx).to_numpy()

    last_seen = pd.concat(
        [train[["home_id", "kickoff"]].rename(columns={"home_id": "t"}),
         train[["away_id", "kickoff"]].rename(columns={"away_id": "t"})]
    ).groupby("t")["kickoff"].max()  # fmt: skip
    new_teams = {
        t for t in teams if t not in last_seen.index or (as_of - last_seen[t]).days > NEW_TEAM_GAP_DAYS
    }
    centre_a = np.array([params.promoted_attack if t in new_teams else 0.0 for t in teams])
    centre_d = np.array([params.promoted_defence if t in new_teams else 0.0 for t in teams])

    def unpack(x):
        return x[0], x[1], x[2 : 2 + n], x[2 + n :]

    def objective(x):
        mu, home, att, dfc = unpack(x)
        eta_h = mu + home + att[hi] - dfc[ai]
        eta_a = mu + att[ai] - dfc[hi]
        lh, la = np.exp(eta_h), np.exp(eta_a)
        nll = np.sum(w * (lh - yh * eta_h)) + np.sum(w * (la - ya * eta_a))
        ra, rd = att - centre_a, dfc - centre_d
        nll += 0.5 * params.reg * (ra @ ra + rd @ rd)
        rh, rah = w * (lh - yh), w * (la - ya)
        g_att = np.bincount(hi, rh, n) + np.bincount(ai, rah, n) + params.reg * ra
        g_def = -np.bincount(ai, rh, n) - np.bincount(hi, rah, n) + params.reg * rd
        grad = np.concatenate([[rh.sum() + rah.sum(), rh.sum()], g_att, g_def])
        return nll, grad

    x0 = np.zeros(2 + 2 * n)
    total_w = w.sum() if len(w) else 1.0
    if len(w):
        x0[0] = np.log(max((w @ (yh + ya)) / (2 * total_w), 0.1))
    x0[2 : 2 + n], x0[2 + n :] = centre_a, centre_d
    res = minimize(objective, x0, jac=True, method="L-BFGS-B")
    mu, home, att, dfc = unpack(res.x)
    fitted = FittedPoisson(
        params=params,
        mu=float(mu),
        home_adv=float(home),
        attack={t: float(att[i]) for t, i in idx.items()},
        defence={t: float(dfc[i]) for t, i in idx.items()},
        new_teams=new_teams,
    )
    if params.fit_rho and len(train):
        fitted.rho = _fit_rho(fitted, train, w, home_col, away_col)
    return fitted


def _dc_tau(x: np.ndarray, y: np.ndarray, lh: np.ndarray, la: np.ndarray, rho: float) -> np.ndarray:
    tau = np.ones_like(lh)
    tau = np.where((x == 0) & (y == 0), 1 - lh * la * rho, tau)
    tau = np.where((x == 0) & (y == 1), 1 + lh * rho, tau)
    tau = np.where((x == 1) & (y == 0), 1 + la * rho, tau)
    tau = np.where((x == 1) & (y == 1), 1 - rho, tau)
    return tau


def _fit_rho(model: FittedPoisson, train: pd.DataFrame, w: np.ndarray, hc: str, ac: str) -> float:
    lam = np.array([model.lambdas(h, a) for h, a in zip(train["home_id"], train["away_id"], strict=True)])
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
