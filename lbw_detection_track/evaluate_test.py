"""Protocol Section 8: the single evaluation of the new test set. Refuses a second run."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from features import SETS, TRACK, at_landmark, load_raw
from methods import SEED
from run_experiments import ids
from scoring import at_threshold, counts, interval, resamples, summary
from sklearn.metrics import average_precision_score, roc_auc_score

LOCKED, OUT, LOG = TRACK / "locked", TRACK / "outputs", TRACK / "sealed" / "test_access.log"
RESAMPLES = 2000


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(record: dict) -> None:
    if LOG.exists():
        raise SystemExit("The test set has already been evaluated. A second run is refused.")
    expected = (TRACK / "sealed/test_ids.sha256").read_text().strip()
    if sha(TRACK / "sealed/test_ids.csv") != expected:
        raise SystemExit("The test list has changed.")
    for name, model in record["models"].items():
        if sha(LOCKED / f"model_set_{name}.joblib") != model["sha256"]:
            raise SystemExit(f"Locked model {name} has changed.")
    forbidden = set(ids("test_ids")) & (set(ids("development_ids")) | set(ids("quarantine_ids")))
    if forbidden:
        raise SystemExit("The test list overlaps development or quarantine records.")


def one_model(y, groups, p, threshold) -> dict:
    row = summary(y, p) | at_threshold(y, p, threshold) | counts(y, p, threshold)
    row["threshold"] = threshold
    draws = {k: [] for k in ("roc_auc", "pr_auc", "sensitivity", "specificity", "ppv", "npv")}
    for picks in resamples(groups, RESAMPLES, SEED):
        if 0 < y[picks].sum() < len(picks):
            yy, pp = y[picks], p[picks]
            draws["roc_auc"].append(roc_auc_score(yy, pp))
            draws["pr_auc"].append(average_precision_score(yy, pp))
            for key, value in at_threshold(yy, pp, threshold).items():
                draws[key].append(value)
    for key, values in draws.items():
        row[f"{key}_low"], row[f"{key}_high"], _ = interval(values)
    return row


def paired(y, groups, new, old, metric, label) -> dict:
    estimate = metric(y, new) - metric(y, old)
    draws = [
        metric(y[i], new[i]) - metric(y[i], old[i])
        for i in resamples(groups, RESAMPLES, SEED)
        if 0 < y[i].sum() < len(i)
    ]
    low, high, se = interval(draws)
    values = np.asarray(draws)
    p = min(1.0, 2 * min((values <= 0).mean(), (values >= 0).mean()))
    return {"comparison": label, "difference": estimate, "low": low, "high": high, "p": p}


def main() -> None:
    record = json.loads((LOCKED / "locked.json").read_text())
    verify(record)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    LOG.write_text(f"{datetime.now(UTC).isoformat()} single evaluation at commit {commit}\n")
    raw = load_raw(ids("test_ids"))
    frame = at_landmark(raw, record["landmark"])
    y, groups = frame["lbw"].to_numpy(), frame["group"].to_numpy()
    probabilities, rows = {}, []
    for name, model in record["models"].items():
        fitted = joblib.load(LOCKED / f"model_set_{name}.joblib")
        p = fitted.predict_proba(frame[SETS[name]].to_numpy(float))[:, 1]
        probabilities[name] = p
        rows.append({"set": name} | one_model(y, groups, p, model["threshold"]))
    pd.DataFrame(rows).to_csv(OUT / "test_results.csv", index=False)
    pairs = []
    for new, old in (("B", "A"), ("C", "B"), ("C", "A")):
        for metric, name in ((roc_auc_score, "ROC AUC"), (average_precision_score, "PR AUC")):
            label = f"{new} over {old}, {name}"
            pairs.append(paired(y, groups, probabilities[new], probabilities[old], metric, label))
    pd.DataFrame(pairs).to_csv(OUT / "test_comparisons.csv", index=False)
    reach = {
        "test_records": len(raw),
        "test_events_all": int(raw["lbw"].astype(int).sum()),
        "at_landmark_records": len(frame),
        "at_landmark_events": int(y.sum()),
    }
    (OUT / "test_reach.json").write_text(json.dumps(reach, indent=1))
    print(json.dumps(reach))
    print(pd.DataFrame(rows).round(4).T.to_string())
    print(pd.DataFrame(pairs).round(4).to_string())


if __name__ == "__main__":
    main()
