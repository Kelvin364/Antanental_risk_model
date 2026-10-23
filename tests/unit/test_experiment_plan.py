"""The prespecified experiment plan of guideline version 2 is complete and parseable."""

import yaml

IDS = {"2.1a", "2.1b", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9"}


def _plan(root):
    return yaml.safe_load((root / "configs" / "experiment_plan.yaml").read_text())


def test_every_experiment_is_listed_with_a_role(root):
    experiments = _plan(root)["experiments"]
    assert {e["id"] for e in experiments} == IDS
    assert all(e["role"] in {"candidate", "descriptive"} for e in experiments)
    assert all("reference" in e or "variants" in e for e in experiments if e["role"] == "candidate")


def test_selection_rule_and_design_are_fixed(root):
    plan = _plan(root)
    rule = plan["selection_rule"]
    assert len(rule["a_replace_only_if_all"]) == 4 and rule["c_if_none_pass"]
    assert plan["design"]["seed"] == 20260930 and plan["design"]["repeats"] == 10
    assert plan["reference_artefact"]["sha256"].startswith("7358b0b2")
    assert "holdout" in plan["design"] and "never" in plan["design"]["holdout"]


def test_no_resampling_experiment_is_planned(root):
    text = (root / "configs" / "experiment_plan.yaml").read_text().lower()
    excluded = _plan(root)["experiments"][2]["excluded"]
    assert excluded == ["oversampling", "undersampling", "synthetic minority generation"]
    assert "smote" not in text
