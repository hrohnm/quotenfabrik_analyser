"""Tippschein decision model: the goal model's probability plus everything else we know, per decision.

For every decision a (multinomial) logistic regression on top of the goal model:
``logit_k = c_k + b · log p_model_k + x · w_k`` with the features of :mod:`decision_features` (standardised,
missing values imputed with the training median plus a missing share per group). The model's probability is
the anchor (``b`` starts at 1, the features only correct it); an L2 penalty keeps useless features near zero.

Walk-forward: every season is predicted by a fit on the seasons before (validation seasons choose the penalty,
test seasons only confirm). The confidence score (0–100) is the rank of the probability of the picked side
among the walk-forward predictions of the same decision: 70 = more confident than 70 % of past fixtures.
"""

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from quotenfabrik.analytics.decision_features import GROUPS

EPS = 1e-6
ALPHAS = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)  # L2 penalty per feature weight (mean log loss scale)
MIN_TRAIN_SEASONS = 2
VALIDATION = (2019, 2020)  # penalty chosen here; later seasons are the test
TEST_FROM = 2021


@dataclass(frozen=True)
class Spec:
    key: str
    classes: tuple[str, ...]  # selections; binary: (yes-side, no-side)
    prob: tuple[str, ...]  # model probability column per class (binary: one column for the first class)
    outcome: str  # outcome column of the first class (winner: three columns)


SPECS = (
    Spec("winner", ("H", "D", "A"), ("p_home", "p_draw", "p_away"), "y_home"),
    Spec("o15", ("over", "under"), ("p_o15",), "y_o15"),
    Spec("o25", ("over", "under"), ("p_o25",), "y_o25"),
    Spec("btts", ("yes", "no"), ("p_btts",), "y_btts"),
    Spec("goal_1h", ("over", "under"), ("p_goal_1h",), "y_goal_1h"),
    Spec("goal_2h", ("over", "under"), ("p_goal_2h",), "y_goal_2h"),
)
BY_KEY = {s.key: s for s in SPECS}


def feature_columns(frame: pd.DataFrame) -> list[str]:
    cols = [c for c in frame.columns if c.startswith(("pat_", "home_", "away_"))]
    return sorted(cols) + (["cup"] if "cup" in frame else [])


def offsets(frame: pd.DataFrame, spec: Spec) -> np.ndarray:
    """log p_model per class (n × K); binary: (log p, log (1 − p))."""
    if len(spec.prob) == 1:
        p = frame[spec.prob[0]].to_numpy(float).clip(EPS, 1 - EPS)
        return np.column_stack([np.log(p), np.log(1 - p)])
    p = frame[list(spec.prob)].to_numpy(float).clip(EPS, 1)
    return np.log(p / p.sum(axis=1, keepdims=True))


def labels(frame: pd.DataFrame, spec: Spec) -> np.ndarray:
    """Index of the class that came true (−1 = not settled)."""
    if spec.key == "winner":
        y = frame[["y_home", "y_draw", "y_away"]].astype(float).to_numpy()
        out = np.where(np.isnan(y).any(axis=1), -1, np.nanargmax(np.nan_to_num(y, nan=-1), axis=1))
        return out.astype(int)
    y = frame[spec.outcome].astype(float).to_numpy()
    return np.where(np.isnan(y), -1, np.where(y > 0.5, 0, 1)).astype(int)


@dataclass
class Prep:
    """Imputation and scaling fitted on the training rows."""

    columns: list[str]
    median: np.ndarray
    mean: np.ndarray
    std: np.ndarray
    groups: dict[str, list[int]]

    @classmethod
    def fit(cls, frame: pd.DataFrame, columns: list[str]) -> "Prep":
        x = frame[columns].to_numpy(float)
        with warnings.catch_warnings():  # all-NaN columns (e.g. absences before 2021) → 0
            warnings.simplefilter("ignore", RuntimeWarning)
            median = np.nan_to_num(np.nanmedian(np.where(np.isfinite(x), x, np.nan), axis=0), nan=0.0)
        filled = np.where(np.isnan(x), median, x)
        mean, std = filled.mean(axis=0), filled.std(axis=0)
        groups = {g: [i for i, c in enumerate(columns) if any(c.endswith(f"_{f}") for f in cols)]
                  for g, cols in GROUPS.items()}  # fmt: skip
        groups["patterns"] = [i for i, c in enumerate(columns) if c.startswith("pat_")]
        return cls(
            columns, median, mean, np.where(std > 1e-9, std, 1.0), {g: v for g, v in groups.items() if v}
        )

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        x = frame.reindex(columns=self.columns).to_numpy(float)
        missing = np.isnan(x)
        z = np.clip((np.where(missing, self.median, x) - self.mean) / self.std, -5, 5)
        flags = [missing[:, idx].mean(axis=1) for idx in self.groups.values()]
        return np.column_stack([z, *flags]) if flags else z

    def to_dict(self) -> dict:
        return {"columns": self.columns, "median": self.median.tolist(), "mean": self.mean.tolist(),
                "std": self.std.tolist(), "groups": self.groups}  # fmt: skip

    @classmethod
    def from_dict(cls, d: dict) -> "Prep":
        return cls(d["columns"], np.array(d["median"]), np.array(d["mean"]), np.array(d["std"]), d["groups"])


@dataclass
class Fit:
    """Fitted coefficients: intercepts ``c`` (K, first fixed at 0), anchor weight ``b``, weights ``w``
    (F, K)."""

    c: np.ndarray
    b: float
    w: np.ndarray

    def logits(self, x: np.ndarray, off: np.ndarray) -> np.ndarray:
        return self.c + self.b * off + x @ self.w

    def predict(self, x: np.ndarray, off: np.ndarray) -> np.ndarray:
        z = self.logits(x, off)
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)


def fit(x: np.ndarray, off: np.ndarray, y: np.ndarray, alpha: float) -> Fit:
    """Penalised maximum likelihood (L-BFGS, analytic gradient); class 0 is the reference."""
    n, f = x.shape
    k = off.shape[1]
    onehot = np.eye(k)[y]

    def unpack(theta):
        c = np.concatenate([[0.0], theta[: k - 1]])
        b = theta[k - 1]
        w = np.column_stack([np.zeros(f), theta[k:].reshape(f, k - 1)])
        return c, b, w

    def loss(theta):
        c, b, w = unpack(theta)
        z = c + b * off + x @ w
        z = z - z.max(axis=1, keepdims=True)
        logp = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
        p = np.exp(logp)
        nll = -(onehot * logp).sum() / n
        pen = alpha * (w**2).sum() + 0.01 * (b - 1) ** 2
        g = (p - onehot) / n  # dL/dz
        grad_c = g.sum(axis=0)[1:]
        grad_b = (g * off).sum() + 0.02 * (b - 1)
        grad_w = (x.T @ g)[:, 1:] + 2 * alpha * w[:, 1:]
        return nll + pen, np.concatenate([grad_c, [grad_b], grad_w.ravel()])

    theta0 = np.concatenate([np.zeros(k - 1), [1.0], np.zeros(f * (k - 1))])
    res = minimize(loss, theta0, jac=True, method="L-BFGS-B", options={"maxiter": 500})
    c, b, w = unpack(res.x)
    return Fit(c, float(b), w)


def log_loss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(p[np.arange(len(y)), y], EPS, 1))


def walk_forward(frame: pd.DataFrame, spec: Spec, alpha: float, seasons: list[int]) -> pd.DataFrame:
    """Predictions for every season in ``seasons`` from a fit on the settled earlier seasons."""
    cols = feature_columns(frame)
    y_all = labels(frame, spec)
    out = []
    for season in seasons:
        train = frame[(frame["season"] < season) & (y_all >= 0)]
        test = frame[frame["season"] == season]
        if train["season"].nunique() < MIN_TRAIN_SEASONS or test.empty:
            continue
        prep = Prep.fit(train, cols)
        model = fit(prep.transform(train), offsets(train, spec), labels(train, spec), alpha)
        p = model.predict(prep.transform(test), offsets(test, spec))
        part = pd.DataFrame(p, columns=list(spec.classes), index=test.index)
        part["fixture_id"] = test["fixture_id"].to_numpy()
        out.append(part)
    return pd.concat(out) if out else pd.DataFrame(columns=[*spec.classes, "fixture_id"])


def choose_alpha(frame: pd.DataFrame, spec: Spec) -> tuple[float, dict]:
    """Penalty with the lowest walk-forward log loss on the validation seasons."""
    y = pd.Series(labels(frame, spec), index=frame.index)
    scores = {}
    for alpha in ALPHAS:
        pred = walk_forward(frame, spec, alpha, list(VALIDATION))
        ok = y.loc[pred.index] >= 0
        p = pred.loc[ok, list(spec.classes)].to_numpy()
        scores[alpha] = float(log_loss(p, y.loc[pred.index][ok].to_numpy()).mean()) if len(p) else np.inf
    return min(scores, key=scores.get), scores


def confidence_table(picked: np.ndarray) -> list[float]:
    """Percentiles 0..100 of the picked side's probability (maps a probability to a confidence score)."""
    return np.percentile(picked, np.arange(101)).tolist() if len(picked) else []


def confidence(picked: np.ndarray, table: list[float]) -> np.ndarray:
    if not table:
        return np.full(len(picked), np.nan)
    return np.interp(picked, table, np.arange(101), left=0, right=100)


def fit_production(frame: pd.DataFrame, spec: Spec, alpha: float) -> dict:
    """Fit on all settled fixtures; payload for :func:`apply` (JSON)."""
    cols = feature_columns(frame)
    y = labels(frame, spec)
    train = frame[y >= 0]
    prep = Prep.fit(train, cols)
    model = fit(prep.transform(train), offsets(train, spec), y[y >= 0], alpha)
    return {
        "decision": spec.key,
        "classes": list(spec.classes),
        "alpha": alpha,
        "prep": prep.to_dict(),
        "c": model.c.tolist(),
        "b": model.b,
        "w": model.w.tolist(),
        "n_train": int(len(train)),
    }


def apply(frame: pd.DataFrame, payload: dict) -> pd.DataFrame:
    """Probabilities per class and the confidence of the picked side with a stored model."""
    spec = BY_KEY[payload["decision"]]
    prep = Prep.from_dict(payload["prep"])
    model = Fit(np.array(payload["c"]), payload["b"], np.array(payload["w"]))
    p = model.predict(prep.transform(frame), offsets(frame, spec))
    out = pd.DataFrame(p, columns=list(spec.classes), index=frame.index)
    out["confidence"] = confidence(p.max(axis=1), payload.get("confidence", []))
    out["fixture_id"] = frame["fixture_id"].to_numpy()
    return out
