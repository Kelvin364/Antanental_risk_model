# Protocol: does incomplete follow up blur the low birth weight signal?

Status: **fixed on 11 November 2026, before any model result of this analysis was computed.** A descriptive count by quarter was seen first and prompted this protocol: in the development pool, the share of recorded low birth weight rises from about 1.5 percent for pregnancies whose last menstrual period fell in late 2023 to about 6.4 percent for late 2024, and the share of recorded preterm births rises with it. Later changes are added at the end as dated amendments.

## 1. Why

The outcome is recorded low birth weight. Two features of how the file was collected can change which births reach it, and neither is about the mother's health:

* **Left truncation.** Pregnancies that began before the register started (2023) enter only if the woman was still pregnant when she first came, so early births are missing from them.
* **Right censoring.** Pregnancies that began late in 2024 have a birth recorded only if it came early, because the extract ended before the others delivered.

Both change the mix of cases between calendar periods. This analysis measures how much that blurs prediction, and whether a cohort with complete follow up gives a clearer, defensible estimate. It also asks which kind of low birth weight the models detect: babies born preterm, or babies born small at term.

Only the track's development pool (5,257 records) is read. The track test set and the quarantine list (the main held out set) are not opened. The served model and the locked week 36 model are not changed.

## 2. Analyses

**F1, description.** By quarter of the last menstrual period: records, recorded low birth weight, and recorded preterm birth. The preterm field is a delivery field. It is used here only to describe, and never as a predictor.

**F2, complete follow up window.** The window is the pregnancies whose last menstrual period is from 1 January 2024 to 30 September 2024. It excludes the 2023 starts (left truncation) and the late 2024 starts (right censoring). The window is known at booking, so a model restricted to it uses no future information. In the window and in the full pool, at landmarks 28 and 36 weeks:

* sets B and D;
* the track's `logistic` and `boosting` methods;
* 5 repeats of 5 folds, grouped by registration group and stratified by outcome, with the track's seed (`run_experiments.out_of_fold`).

Out of fold ROC AUC is reported with a 95 percent interval from 2,000 resamples of registration groups (seed 20261111).

**F3, which cases are detected.** For each F2 configuration, from the same out of fold scores, ROC AUC is computed separately:

* term low birth weight cases against all births that were not low birth weight;
* preterm low birth weight cases against the same comparison group.

This is evaluation only. It cannot select women in practice, because term or preterm is known only at birth.

## 3. Decision rules fixed in advance

* F2 shows that follow up blurs the signal if the window's ROC AUC is higher than the full pool's for the same configuration in at least three of the four configurations at a landmark. That is a description, not a test: the two populations differ, so no paired interval is claimed.
* F3 shows that the models detect small term babies better than preterm babies if the term ROC AUC interval lies wholly above the preterm point estimate.
* No result here replaces a sealed test result. Every number is internal validation.

## Amendments

None yet.
