"""The smallest paired difference this design could reliably detect (Section 3.3.9).

With a bootstrap standard error ``se`` for a paired difference, a two sided
test at level ``alpha`` detects a true difference ``d`` with probability
``power`` when ``d = (z(1 - alpha / 2) + z(power)) * se``. At alpha 0.05 and
power 0.80 that is about 2.8 standard errors. A null result is then read as
"no difference of at least this size", not as inconclusive by default.
"""

from __future__ import annotations

from statistics import NormalDist


def detectable_difference(bootstrap_se: float, alpha: float = 0.05, power: float = 0.80) -> float:
    """Smallest true difference detected with ``power`` at two sided level ``alpha``."""
    if bootstrap_se < 0:
        raise ValueError("A standard error cannot be negative")
    z = NormalDist().inv_cdf
    return (z(1 - alpha / 2) + z(power)) * bootstrap_se
