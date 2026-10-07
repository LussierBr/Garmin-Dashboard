"""Predict tonight's sleep score from today's steps (and optionally more).

Ordinary least squares with a quadratic step term, so the model can capture
"more steps help, up to a point". The uncertainty band is a proper 80%
prediction interval for a single night, not just the uncertainty of the mean.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as st

TARGET = "tonight_sleep_score"
EXTRA_FEATURES = {"avg_stress": "Today's average stress", "sleep_score": "Last night's sleep score"}


@dataclass
class SleepModel:
    features: list[str]
    beta: np.ndarray
    xtx_inv: np.ndarray
    sigma: float
    dof: int
    n: int
    r2: float
    holdout_mae: float
    baseline_mae: float
    medians: dict
    step_range: tuple[float, float]

    def _design(self, rows: pd.DataFrame) -> np.ndarray:
        k = rows["steps"].to_numpy(float) / 1000
        cols = [np.ones(len(rows)), k, k**2] + [rows[f].to_numpy(float) for f in self.features if f != "steps"]
        return np.column_stack(cols)

    def predict(self, steps: float, level: float = 0.80, **extras) -> dict:
        row = {"steps": steps, **{f: extras.get(f, self.medians[f]) for f in self.features if f != "steps"}}
        X = self._design(pd.DataFrame([row]))
        mean = float((X @ self.beta)[0])
        se = self.sigma * np.sqrt(1 + float((X @ self.xtx_inv @ X.T)[0, 0]))
        t = st.t.ppf(0.5 + level / 2, self.dof)
        return {"mean": mean, "low": mean - t * se, "high": mean + t * se, "se": se,
                "extrapolating": not (self.step_range[0] <= steps <= self.step_range[1])}

    def curve(self, level: float = 0.80, points: int = 80) -> pd.DataFrame:
        xs = np.linspace(*self.step_range, points)
        rows = [self.predict(x, level) | {"steps": x} for x in xs]
        return pd.DataFrame(rows)


def _ols(X: np.ndarray, y: np.ndarray):
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    return beta, xtx_inv


def fit(df: pd.DataFrame, extra: list[str] | None = None) -> SleepModel | None:
    feats = ["steps"] + list(extra or [])
    d = df[feats + [TARGET]].dropna().reset_index(drop=True)
    if len(d) < 30:
        return None

    proto = SleepModel(feats, np.zeros(0), np.zeros((0, 0)), 0, 0, 0, 0, 0, 0, {}, (0, 0))
    X, y = proto._design(d), d[TARGET].to_numpy(float)

    # Honest check: train on the earlier 80% of days, score on the most recent 20%.
    cut = int(len(d) * 0.8)
    b_tr, _ = _ols(X[:cut], y[:cut])
    holdout_mae = float(np.mean(np.abs(X[cut:] @ b_tr - y[cut:])))
    baseline_mae = float(np.mean(np.abs(y[:cut].mean() - y[cut:])))

    beta, xtx_inv = _ols(X, y)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    sigma = float(np.sqrt(resid @ resid / dof))
    r2 = float(1 - (resid @ resid) / np.sum((y - y.mean()) ** 2))
    lo, hi = d["steps"].quantile([0.02, 0.98])
    return SleepModel(feats, beta, xtx_inv, sigma, dof, len(y), r2, holdout_mae, baseline_mae,
                      {f: float(d[f].median()) for f in feats}, (float(lo), float(hi)))
