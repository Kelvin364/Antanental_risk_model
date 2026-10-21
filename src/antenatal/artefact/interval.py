"""Coefficient covariance and the Wald interval on one predicted probability.

The interval of Table 3.7 is a confidence interval for the estimated
probability, arising from uncertainty in the fitted coefficients. It is not a
prediction interval for the individual outcome.

Algorithm. For the fitted L2 penalised logistic regression, with design matrix
``Z`` (the imputed and scaled features after the pipeline's preprocessing,
plus a column of ones for the intercept) and fitted probabilities ``p``, the
covariance of the coefficients is the inverse of the penalised Hessian
``Z' W Z + P / C``, where ``W`` is diagonal with ``p (1 - p)`` and ``P`` is the
identity with a zero for the intercept. For a new case with design row ``z``
the logit is ``eta = z' beta`` with standard error ``sqrt(z' V z)``, and the
interval is the inverse logit of ``eta`` plus or minus 1.96 standard errors.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from antenatal.evaluation.metrics import sigmoid

Z_95 = 1.959963984540054


def design_rows(pipeline: Pipeline, x: pd.DataFrame) -> np.ndarray:
    """Preprocess ``x`` with every step but the estimator and prepend the intercept column."""
    z = pipeline[:-1].transform(x)
    return np.column_stack([np.ones(len(z)), z])


def coefficient_covariance(pipeline: Pipeline, x_train: pd.DataFrame) -> np.ndarray:
    """Inverse penalised Hessian of a fitted L2 logistic pipeline, intercept first."""
    model = pipeline[-1]
    z = design_rows(pipeline, x_train)
    beta = np.concatenate([model.intercept_, model.coef_[0]])
    p = sigmoid(z @ beta)
    hessian = z.T @ (z * (p * (1 - p))[:, None])
    penalty = np.eye(len(beta)) / model.C
    penalty[0, 0] = 0.0
    return np.linalg.inv(hessian + penalty)


def wald_interval(
    pipeline: Pipeline, covariance: np.ndarray, x: pd.DataFrame, z_value: float = Z_95
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Probability, lower bound and upper bound for every row of ``x``."""
    model = pipeline[-1]
    z = design_rows(pipeline, x)
    beta = np.concatenate([model.intercept_, model.coef_[0]])
    eta = z @ beta
    se = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", z, covariance, z), 0.0))
    return sigmoid(eta), sigmoid(eta - z_value * se), sigmoid(eta + z_value * se)
