# Evidence review behind the protocol

Reviewed on 7 November 2026 through web search of published work. Most entries were read as abstracts or search summaries, not full text, and the last section says which claims could not be confirmed. Check a paper in full before quoting it to the panel.

## What performance is realistic

* A 2025 systematic review and meta analysis of 90 studies of machine learning for adverse perinatal outcomes reported a median internal validation AUC of 0.68 for small for gestational age, with nearly all studies at high risk of bias. Performance was moderate and no universally strong predictor emerged. This is the closest benchmark found, and it sits near the study's development ROC AUC of 0.63.
* First trimester screening for small for gestational age using maternal factors with biochemistry detected about 27 percent at a 5 percent false positive rate (Poon et al., 2008, Nicolaides group). Early screening does much better for early, severe cases than for late ones (Crovetto et al., 2013).
* Later assessment detects far more. A third trimester strategy reached a 79 percent detection rate at a 25 percent screen positive rate, but with ultrasound and a first trimester model (Souka, Papastefanou et al., 2012).

**Consequence for this track:** the time of prediction is likely to matter more than the algorithm, so the protocol tests later landmarks. The ultrasound signal behind the best published results is largely absent from this file (recorded for about 4 percent of development records at visit three).

## Published results that look far better, and why they are not targets

* Bekele (2022), Ethiopia: random forest, 91.6 percent recall, ROC AUC 0.968. Ngusie et al. (2024), sub Saharan Africa: AUC 0.95 with data balancing and an 80 to 20 split. Summaries do not show whether balancing happened before the split. If it did, copies of test cases are in training and the scores are inflated. Survey predictors can also include birth time information. A Bangladesh survey analysis found pregnancy duration the strongest predictor, which is not known in advance.
* Oktarina et al. (2023), Indonesia: SMOTE with a random forest gave sensitivity 31 percent, specificity 83.6 percent and AUC 0.62, close to this study.
* Small cohorts with risk scores: Ethiopia, 379 women, AUC 0.83; Uganda, sensitivity 79.1 percent, specificity 72.9 percent and AUC 0.82 with uterine artery Doppler and synthetic oversampling. Neither is comparable: one is very small and the other uses a Doppler measure this file does not hold.

**Consequence:** every step that learns from data runs inside the training fold, and birth time fields are banned.

## Class imbalance

* van den Goorbergh et al. (2022, JAMIA): random undersampling, random oversampling and SMOTE gave poorly calibrated logistic models with no higher ROC AUC than no correction. Moving the probability threshold gave similar sensitivity and specificity gains.
* Carriero et al. (2024 preprint) extended this to machine learning models: uncorrected models had equal or better calibration, and recalibration did not always repair corrected models.

**Consequence:** weighting and SMOTE are tested because the author asked, inside folds, against the plain model. The expected route to high sensitivity is threshold choice.

## Candidate predictors

* Symphysis fundal height: sensitivity for small for gestational age ranged from 0.27 to 0.76 (Pay et al., 2015), and a meta analysis judged it unsuitable for primary screening (Goto). In this file it is almost always recorded "normal" (9 of 3,126 abnormal at visit one in the development records), so it cannot help.
* Gestational weight gain is linked to low birth weight in South Asia and sub Saharan Africa, modified by early body mass index (BMJ Public Health, 2025). This supports weight gain per week and body mass index in sets C and D.
* Prior low birth weight is a known predictor in one seven algorithm study (AUC 0.778), but that study also used preterm birth, which is not available in advance. This file does not record prior birth weight usably.

## Sample size

Riley and colleagues set out methods for the size of validation samples, and a worked example needed 116 events to estimate net benefit precisely. Dhiman et al. (2023) found only 9 of 119 development studies justified their sample size. The new test set is expected to hold far fewer than 116 events, so its intervals will be wide and the report must say so.

## Not confirmed

* Christodoulou et al. (2019), the review finding no advantage of machine learning over logistic regression, did not appear in the search. It is well known, but was not checked here.
* A 2024 review reporting sensitivity and AUC near 100 percent for adverse pregnancy outcomes could not be verified.
* No Tanzania specific low birth weight machine learning study was found.

## Sources

* https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9382395/
* https://arxiv.org/html/2404.19494v1
* https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4328041/
* https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7290279/
* https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9443037/
* https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12483264/
* https://zendy.io/title/10.1002/sim.9025
* https://zendy.io/title/10.1002/pd.2143
* https://zendy.io/title/10.1002/uog.12537
* https://www.pubmed.gov/23754253/
* https://doaj.org/article/eeda00dfed4b4db3a4d5eeb3f8689278
* https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1484299/pdf
