# Ethics and responsible AI

This one document holds everything about the ethics of the study and of the prediction model it builds: the ethical basis of the data, how the data are used, the safeguards built into the model and the application, and the reporting items that only the author can complete. It answers TRIPOD+AI item 17 (ethical approval) as far as the sources allow, and it collects the TRIPOD+AI items 2, 18a to 18d, 19 and 27c that await the author. TRIPOD+AI is the reporting guideline for clinical prediction models that use regression or machine learning.

Sections marked **AUTHOR TO WRITE** contain statements that only the author can give. Nothing in them has been written on the author's behalf.

## 1. The dataset

| Item | Value | Source |
| --- | --- | --- |
| Title | Dataset for Maternal Health Risks Stratification (MHRS) in Tanzania | Zenodo record 15309733 |
| Authors | Mwifunyi, R., Kibinda, N., Elisa, N., Rashidi, F. U., Hassan, K., Mohsini, M., Masoi, T., Mnabwiru, L., Hussein, Y., and Manangwa, S. | Zenodo record 15309733 |
| Version used | Version 1, published 30 April 2025 | Zenodo record 15309733 |
| File used | `maternal_dataset_csv.csv`, SHA 256 recorded in `data/README.md` and verified on every load | This repository |
| Newer version | A newer version exists on Zenodo. This study stays on version 1 because the specification and every count were frozen against its checksum | Zenodo record 15309733 |
| Licence | Creative Commons Attribution 4.0 International | Zenodo record 15309733 |
| Funders named on the record | Wellcome Trust; Lacuna Fund, grant 228079 | Zenodo record 15309733 |
| Collection period | 20 May 2024 to 30 March 2025 | Zenodo record 15309733 |
| Setting | Pregnant women attending maternity primary health facilities in Chamwino, Mkuranga, Meatu, Mbulu and Kilolo districts | Zenodo record 15309733 |
| DOI | https://doi.org/10.5281/zenodo.15309733 | |

## 2. Ethical approval and consent

### 2.1 Statement of the data producers

**Status.** The release contains no ethics approval or consent statement. A request for the producers' statement was sent to them on 21 October 2026. Until a reply is received, the placeholder below stays in place.

> **PLACEHOLDER: no statement found yet.** The Zenodo record page
> (https://zenodo.org/records/15309733) and its `metadata.pdf`, a field
> dictionary, were read on 21 October 2026. Neither contains a statement on
> ethical approval, the approving committee, a permit or reference number,
> informed consent, or de-identification. The record links no data paper.
> No wording has been paraphrased or reconstructed here. When the producers'
> statement is obtained, quote it here exactly, with the document and page or
> section.

### 2.2 University determination

> **AUTHOR TO WRITE.** The proposal states that the study follows the African
> Leadership University's decision on the ethics of secondary data and claims
> no exemption. Record that decision here when it is received: the deciding
> body, the date, any reference number, and its conditions.

### 2.3 Gaps found

1. **No published ethics or consent statement.** The release does not state which body approved the original collection or how consent was obtained. Reuse here rests on the CC BY 4.0 licence and on the data containing no direct identifiers.
2. **Identifiers.** The file has no names, facility identifiers or geographic coordinates. It does hold exact dates (last menstrual period, expected delivery) and registration details. Records that share age, last menstrual date, height, weight and prior deliveries are grouped in the analysis, and only a short hash of that key is published in `outputs/cohort_manifest.csv`.
3. **Suspect fields.** The data audit found history fields that agree with delivery outcomes far more than real history should. They are excluded as predictors pending clarification from the publisher (proposal Table 3.3; `docs/implementation_audit.md`).

## 3. How the data are used

* The raw file is opened for reading only and never modified. Its SHA 256 is verified before every load.
* No attempt is made to re-identify anyone, and the data are not linked to any other source.
* No output informs the care of any pregnant woman.
* The application accepts synthetic cases only. It refuses to save a case without the synthetic flag and says so on every screen. The online deployment serves synthetic cases only: requirement R14 is revised to "no real patient record is entered, stored or transmitted" (supervisor decision of 23 October 2026, D2 in `docs/decisions_log.md`; `docs/deviations.md`).

## 4. Safeguards built into the model

### 4.1 The held out records and bias

A model judged on records it has already seen looks better than it is, so the held out records are kept out of every step that learns from data. This is the one absolute rule of the study (decision D7 in `docs/decisions_log.md`). On 24 October 2026 the author reported that the supervisor approved the held out evaluation and asked that, whatever else is done, the held out records must never be found in the training pipeline, to avoid bias.

How this is enforced:

* The 782 held out records (41 events) were sealed in `partitions/holdout_ids.csv` before any model was fitted, and the file's checksum is tested.
* Every model fit carries a `TrainingGuard` that refuses any data containing a held out record.
* Every step that learns from data (imputation, scaling, the availability screen, tuning) runs inside the training fold only.
* `python -m antenatal audit-holdout` checks this without reading any held out outcome; its eleven checks are recorded in `docs/evidence/holdout_integrity.md`.
* The held out outcomes are read once only, through `HoldoutEvaluator.evaluate_once`, on models locked beforehand, by the protocol in `docs/holdout_protocol.md`. Every access is logged in `partitions/holdout_access.log`, and nothing about the model may change because of the result.

### 4.2 What the model outputs, and what it does not

* The model ranks pregnancies by their estimated probability of a recorded birth weight below 2.5 kg. It is a research estimate from one Tanzanian dataset, not validated for any pregnancy, not a diagnosis and not a recommendation for care. That limitation line is shown on every screen and on every figure.
* The only label is "Likely" or "Not likely low birth weight" at a threshold fixed on development records (`webapp/model/classification.json`, decision D6). It is always shown with how far it can be trusted: sensitivity, specificity and predictive values with intervals, and whether the case's own interval crosses the threshold.
* There is no priority label, triage band or "see sooner" wording anywhere in the code, text, figures or designs.

### 4.3 Fairness

Performance is reported for age bands and parity, the only population characteristics in the file that allow it (`outputs/tables/subgroups.csv`; TRIPOD+AI item 14). A subgroup is reported only when it holds at least 30 events. Other characteristics that matter for fairness, such as region, income or facility, are not available, so the model's behaviour across them is unknown. This is stated as a limitation.

### 4.4 Choices that could hide or create bias

* Class weighting and resampling were allowed only inside training folds (decisions D4 and D7). None of the Stage 2 experiments that used them passed the prespecified selection rule, so the served model uses neither.
* Missing measurements are imputed with values learned from the training fold, with missingness indicators. Whether missingness itself carries signal is tested in research question 4 (`docs/research_results.md`).
* Eligibility uses facts known only after delivery (a weighed singleton live birth), so the model applies only to that population. A pregnancy ending in a stillbirth, a multiple birth or an unrecorded weight is outside what it has learned.

## 5. Safeguards built into the application

* Every case, visit, assessment and caseload route requires a signed in user with the administrator or researcher role (decision D1). There is no self sign up.
* Passwords are stored as scrypt hashes, sessions are server side and end on sign out, every change carries a token against cross site requests, and repeated failed sign ins lock the account.
* An audit trail records who did what, without storing any clinical value.
* Researchers see only their own cases.

## 6. Use of AI assistance in producing this work

> **AUTHOR TO WRITE.** State how AI tools were used in producing the code,
> analysis and text of this project, which tools, for which parts, and how
> their output was checked, following the university's policy on AI use.

## 7. TRIPOD+AI items awaiting the author

Write each answer under its prompt, then move it into `docs/Technical-Report.md` (or the template it is generated from) and mark the item Reported in `docs/tripod_ai_checklist.md`.

### Item 2. Abstract

> **AUTHOR TO WRITE.** A structured summary following the TRIPOD+AI for
> Abstracts checklist: objective, design, setting, participants, predictors,
> outcome, analysis, results with intervals, conclusion.

### Item 18a. Funding

> **AUTHOR TO WRITE.** Name every source of funding for this study and the
> funder's role, or state that the study received no specific funding.

### Item 18b. Conflicts of interest

> **AUTHOR TO WRITE.** Declare any financial or other interests of the author
> and supervisor, or state that there are none.

### Item 18c. Protocol

> **AUTHOR TO WRITE.** Say where the frozen protocol (the proposal) can be
> read, for example a repository path or a university record.

### Item 18d. Registration

> **AUTHOR TO WRITE.** Give the registry name and number, or state that the
> study was not registered.

### Item 19. Patient and public involvement

> **AUTHOR TO WRITE.** Describe any involvement of patients or the public in
> design, conduct, reporting or dissemination, or state that there was none.

### Item 27c. Next steps

> **AUTHOR TO WRITE.** Describe the next research steps, with a view to
> applicability, for example external validation in a Rwandan cohort.

## 8. Walkthrough with health workers

A walkthrough of the prototype with two or three health workers or clinicians, using synthetic cases only, is a **proposed activity** (proposal Sections 1.5 and 3.6). It has **not taken place**. It is pending the African Leadership University's determination, and it will not start before that determination is received and recorded in section 2.2. It is not on the critical path of the study and is not a clinical evaluation.
