# Decisions log

One dated entry per decision that changes the plan or the proposal. Each entry says who made the decision, what it changes, and the row it adds to the proposal modification table. The source for D1 to D3 is the author's account of the supervisor meeting of 23 October 2026, as written in guideline version 2; this log records that account and adds nothing to it.

Engineering choices made under the decision rules of guideline version 2 are listed at the end, with the rule applied.

## D1. Authentication is required (23 October 2026)

* **Decided by:** the supervisor, Emmanuel Adjei, at the meeting of 23 October 2026, as reported by the author.
* **Decision:** no case, visit, assessment or caseload route is reachable without a signed in user. Two roles: administrator and researcher.
* **What it changes:** the sign in screens return to the interface design (proposal Figure 3.6). Figure 3.7 gains the administrator and researcher actors and a user entity. The earlier project rule "no sign in, sign up, accounts or sessions" is withdrawn; the rule against clinical risk categories, priority labels and triage wording stays.
* **Proposal modification table row:** "Figure 3.6 and Figure 3.7: authentication with administrator and researcher roles added, supervisor decision of 23 October 2026."

## D2. Online deployment is required, synthetic cases only (23 October 2026)

* **Decided by:** the supervisor, at the meeting of 23 October 2026, as reported by the author.
* **Decision:** the application is deployed online. It accepts synthetic cases only and stores no identifiers.
* **What it changes:** requirement R14 is revised from "transmit no record outside the local environment" to "no real patient record is entered, stored or transmitted". The cloud hosting budget line in the proposal is used. Table 3.12 gains the hosting platform once it is chosen; the database stays SQLite unless concurrency on the host requires PostgreSQL.
* **Proposal modification table row:** "R14 revised to: no real patient record is entered, stored or transmitted. Online deployment of synthetic cases only, supervisor decision of 23 October 2026."

## D3. Improve the model under a prespecified rule, then one held out evaluation (23 October 2026)

* **Decided by:** the supervisor, at the meeting of 23 October 2026, as reported by the author.
* **Decision:** run the experiments listed in `configs/experiment_plan.yaml` on development records only, choose a candidate with the selection rule written in that file before any experiment runs, and evaluate the locked candidate once on the held out partition.
* **What it changes:** the sentence that opens the held out partition becomes "supervisor approved on 23 October, run the holdout on artefact <version>", and it applies only to a candidate locked by the selection rule. The frozen artefact 1.0.0 stays served unless a candidate passes that rule. Proposal Section 3.3.6 (model choice) and Section 3.3.7 (evaluation) gain a reference to the prespecified plan.
* **Proposal modification table row:** "Sections 3.3.6 and 3.3.7: prespecified model improvement experiments with a written selection rule before the single held out evaluation, supervisor decision of 23 October 2026."

## D4. Class weighting admitted as one prespecified experiment (23 October 2026)

* **Decided by:** the author, through guideline version 2 experiment 2.2, and within what the supervisor allows under D7.
* **Decision:** logistic regression and gradient boosting with balanced class weights are evaluated on sets B and C against their unweighted versions. Oversampling, undersampling and synthetic minority generation remain excluded.
* **What it changes:** the earlier project rule excluded class weighting everywhere, in line with the proposal. Weighting is now an experiment only. A weighted model can be served only if it passes the selection rule, including the calibration condition, possibly paired with cross fitted recalibration.
* **Proposal modification table row:** "Section 3.3.5: class weighting evaluated as one prespecified experiment; resampling still excluded."

## D5. Guideline numbering resolved (23 October 2026)

* **Decided by:** Claude Code, under decision rule 3 (amend, do not ignore), to be confirmed by the author.
* **Decision:** guideline version 2 asks to replace "rule 6" with the authentication rule. In the project rules, rule 6 defines set C for linear models and rule 7 is the rule against sign in and accounts. The authentication sentence replaces the first sentence of rule 7; rule 6 is kept unchanged, and the rest of rule 7 (no risk categories or triage wording) is kept.
* **What it changes:** nothing in the proposal.

## D6. The application labels each case at a fixed threshold, with its confidence (23 October 2026)

* **Decided by:** the author, in this session, choosing a yes or no label with its confidence over a probability without a label.
* **Decision:** each assessment shows "Likely low birth weight" or "Not likely low birth weight". The threshold is the predicted probability that marks the highest 20 percent of the served model's out of fold predictions on development records, the middle of the proposal's ranking budgets: 0.0688 for artefact 1.0.0 (`webapp/model/classification.json`, written by `python -m antenatal freeze-classification`). Beside the label the application shows the threshold's sensitivity, specificity and predictive values with group bootstrap intervals, and whether the case's own 95 percent interval lies above, below or across the threshold.
* **What it changes:** requirement R11 ("rank and probability with interval, no category") becomes "rank, probability with interval, and a label at a prespecified threshold shown with how often the label is right". The limitation line now reads "Not a diagnosis and not a recommendation for care". Triage, priority and "see sooner" wording stays excluded. Stage 4 evaluates the label at the same fixed threshold on the held out partition. A locked model of a later version gets its own threshold by the same rule before the holdout run.
* **Proposal modification table row:** "R11 and Table 3.10 screen 4: a label at a prespecified threshold (highest 20 percent of out of fold predictions) is shown with its sensitivity, specificity and predictive values and the case's interval position, author decision of 23 October 2026."
* **Supervisor position:** within what the supervisor allows under D7.

## D7. One absolute rule: held out records never reach training; host online with a local backup (23 October 2026)

* **Decided by:** the supervisor, as reported by the author.
* **Decision:** the only thing not allowed is for the held out records to enter the training pipeline in any form, so that no model can learn or adapt to the test data. Everything else in the plan may be done, with care in how it is shown that the test data was not compromised. The whole system is hosted online, and the local environment is kept as a working backup.
* **What it changes:**
  * Class weighting (D4) and the label at a threshold (D6) are within what the supervisor allows; resampling methods are allowed too, inside training folds only.
  * The held out rule is now enforced in code, not only by convention. Every model fit requires a `TrainingGuard` that refuses any frame containing a held out record, and `python -m antenatal audit-holdout` writes ten checks to `docs/evidence/holdout_integrity.md`. The checks cover record and group overlap, stored predictions, the served reference caseload, identical predictor vectors and the count of held out evaluations. None reads a held out outcome.
  * To keep the test uncompromised in the second way it can be, by being used to choose, the held out records are still evaluated once on a locked model. Any later evaluation is labelled exploratory and counted by the audit.
  * Deployment moves from optional to required, with `make serve` and `make docker` kept as the local backup.
* **Proposal modification table row:** "Section 3.3.7: the held out partition is guarded in code and audited by ten recorded checks; Section 3.5: the system is hosted online with a local backup, supervisor decision of 23 October 2026."

## Engineering choices under the decision rules

| Date | Choice | Rule applied |
| --- | --- | --- |
| 23 October 2026 | Git tag `pre-v2` on commit `6e291f4`, and a copy of `webapp/model/` with checksums in `backups/model_v1.0.0/` (kept outside git, which already holds the same files under the tag) | Rule 1, evaluation integrity; guideline Stage 0.3 |
| 23 October 2026 | Experiment 2.3 lists "set B plus each single visit two measurement in turn". Set B already holds every visit two measurement, so the plan reads it as set A plus each single visit two measurement, against set A | Rule 5, honesty; to be confirmed by the author |
| 23 October 2026 | The selection rule's "Brier is not worse" is fixed as: the 95 percent interval of candidate minus artefact Brier has its lower bound at or below zero, so a candidate is refused only when its Brier is clearly worse | Rule 2, prespecification; written before any experiment ran |
| 23 October 2026 | Passwords are hashed with scrypt from the Python standard library instead of passlib with bcrypt, which is no longer maintained; no new dependency is needed | Rule 4, simpler; rule 6, security |
| 23 October 2026 | Sessions are random tokens stored as SHA 256 hashes on the server rather than signed cookies, so signing out ends a session on the server and there is no signing key to manage | Rule 6, security beats convenience |
| 23 October 2026 | The content security policy forbids evaluating strings as code; the browser tests wait for page content with locators instead of evaluated expressions, so the policy is not weakened for tests | Rule 6 |
| 23 October 2026 | Deployment waits for authentication: a route is protected on the server or it is not deployed | Rule 6 |
| 23 October 2026 | The three spline knots of experiment 2.4 are placed at the 10th, 50th and 90th percentiles of each training fold, the usual placement for three knots | Rule 2, prespecification; rule 1, knots come from the training fold only |
