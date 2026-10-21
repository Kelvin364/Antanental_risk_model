"""Refitting the primary configuration reproduces the committed model.

A refit cannot reproduce the file byte for byte, because the artefact class
gained a field after the primary artefact was frozen. So reproducibility is
judged on the model content: feature names, coefficients, intercept,
penalty and reference probabilities must match to 1e-9. The file checksum is
tested only for the committed artefact, in ``tests/unit``.
"""

import numpy as np
import pytest

from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.paths import ProjectPaths
from antenatal.study import freeze_artefact

pytestmark = pytest.mark.slow
TOLERANCE = 1e-9


@pytest.fixture(scope="module")
def pair(tmp_path_factory, root):
    project = tmp_path_factory.mktemp("refit")
    (project / "data").mkdir()
    (project / "data" / "maternal_dataset_csv.csv").symlink_to(
        root / "data" / "maternal_dataset_csv.csv"
    )
    (project / "outputs").symlink_to(root / "outputs")
    (project / "partitions").symlink_to(root / "partitions")
    refit = freeze_artefact(ProjectPaths.from_root(project))
    committed = FittedPipelineArtefact.load(root / "webapp" / "model")
    return committed, refit


def test_feature_names_match(pair):
    committed, refit = pair
    assert refit.feature_names == committed.feature_names


def test_coefficients_and_intercept_match(pair):
    committed, refit = pair
    old, new = committed.pipeline[-1], refit.pipeline[-1]
    np.testing.assert_allclose(new.coef_, old.coef_, rtol=0, atol=TOLERANCE)
    np.testing.assert_allclose(new.intercept_, old.intercept_, rtol=0, atol=TOLERANCE)
    assert new.C == old.C


def test_reference_probabilities_match(pair):
    committed, refit = pair
    np.testing.assert_allclose(
        refit.reference_probabilities, committed.reference_probabilities, rtol=0, atol=TOLERANCE
    )
