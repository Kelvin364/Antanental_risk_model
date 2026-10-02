# Antenatal Caseload Prediction

### Incremental value of two antenatal measurements for predicting recorded low birth weight in a Tanzanian cohort

**Kelvin Rwihimba**, BSc Software Engineering (Machine Learning), African Leadership University.
Capstone project: model notebook, frozen model artefact, prediction API, and prototype interface.

![Caseload screen](antenatal-caseload-prediction/designs/web/07-caseload.png)

---

## Links

| | |
| --- | --- |
| **GitHub repository** | https://github.com/Kelvin364/Antanental_risk_model |
| **Demo video** | https://youtu.be/QN0X9P8TFkA |
| **Figma design file** | https://www.figma.com/design/UHmymjrnb2HJX47uQzf4jg |
| **Local interface** | http://127.0.0.1:8000/ (after setup below) |
| **Interactive API docs** | http://127.0.0.1:8000/docs |

> **Synthetic data only in the prototype. Not a medical device and not for clinical use.**
> The interface demonstrates how the study's model would be packaged for a community health
> worker. It makes no care decisions and shows no clinical risk category.

---

## Table of contents

1. [What this project is](#1-what-this-project-is)
2. [The research question and the answer](#2-the-research-question-and-the-answer)
3. [Repository structure](#3-repository-structure)
4. [End to end walkthrough](#4-end-to-end-walkthrough)
5. [Dataset](#5-dataset)
6. [Environment and setup](#6-environment-and-setup)
7. [Running the notebook](#7-running-the-notebook)
8. [Running the web application](#8-running-the-web-application)
9. [API reference](#9-api-reference)
10. [The interface: navigation and layout](#10-the-interface-navigation-and-layout)
11. [Designs](#11-designs)
12. [Results in detail](#12-results-in-detail)
13. [Design decisions and why](#13-design-decisions-and-why)
14. [Reproducibility and integrity](#14-reproducibility-and-integrity)
15. [Scope, limitations, and safety](#15-scope-limitations-and-safety)
16. [Troubleshooting](#16-troubleshooting)
17. [Sources](#17-sources)
18. [Licence](#18-licence)

---

## 1. What this project is

A community health worker visits the same pregnant woman more than once. A paper checklist reads
one visit at a time. This project asks whether the **second** antenatal visit, and the **change**
since the first visit, carry a warning signal for **low birth weight** (a recorded birth weight
below 2.5 kg) beyond what is already known at registration, using only measurements obtainable
**without a laboratory**.

The project delivers three things that fit together.

**1. A model notebook** (`notebook/Model-Notebook.ipynb`) that runs top to bottom on a real
Tanzanian antenatal dataset. It builds three nested feature sets, compares eight traditional
models, measures the incremental value with paired bootstrap intervals, reports how large an effect
the study could even detect, checks a sealed hold out once, and saves a frozen model artefact with
a checksum.

**2. A prediction service** (`webapp/`) built on FastAPI plus a no build single page interface. It
loads the frozen artefact and never retrains, verifies its SHA-256 on startup, and returns a
calibrated probability, a 95 percent interval, and a **caseload position** (percentile in the study
cohort).

**3. A design set** (`designs/`) holding seven full resolution web screens plus the editable Figma
file.

The honest framing matters here. Many earlier studies on similar data reported strong results while
oversampling or re weighting the rare outcome, which quietly inflates the numbers. This notebook
does neither, so the figures it reports are the ones a real deployment would see.

---

## 2. The research question and the answer

**Question.** At the second antenatal visit, do that visit's measurements and the change since the
first visit predict recorded low birth weight any better than registration information alone?

**Answer: no, not at a size this study could detect.**

| | |
| --- | --- |
| Study group | **3,908** pregnancies |
| Low birth weight cases | **206** (5.27 percent) |
| Guessing level (PR AUC equals prevalence) | **0.053** |
| PR AUC, set A (registration) | **0.073** |
| PR AUC, set B (A plus visit two) | **0.074** |
| PR AUC, set C (A plus visit two plus change) | **0.074** |

Paired comparisons for the chosen model (logistic regression), 95 percent bootstrap intervals over
2,000 resamples of the same pregnancies and the same predictions.

| Comparison | Change in PR AUC | 95 percent interval | Verdict |
| --- | --- | --- | --- |
| B over A, the second visit | plus 0.002 | minus 0.014 to plus 0.014 | no gain we can trust |
| C over B, the change | minus 0.001 | minus 0.007 to plus 0.005 | no gain we can trust |
| C over A, both together | plus 0.001 | minus 0.016 to plus 0.014 | no gain we can trust |

The result holds across eight model families and both metrics, and the smallest gain the study
could reliably detect (about 0.020 PR AUC, about 0.041 ROC AUC) is an order of magnitude larger
than the gains observed. The honest reading is not that we narrowly missed a small benefit, but
that any benefit, if it exists, is too small to matter at this event count.

What the project still delivers is a **trustworthy ranking tool**. The chosen model's probabilities
can be taken at face value, so pregnancies can be ordered by who to see first.

---

## 3. Repository structure

```
Antanental_risk_model/
   Readme.md                           this file, the only README in the project
   antenatal-caseload-prediction/
      LICENSE                          MIT
      notebook/
         Model-Notebook.ipynb          the full study: 60 cells, 14 sections, 13 figures
         requirements.txt              notebook dependencies
      data/
         (empty)                       the raw dataset goes here, it is not committed
      webapp/
         app/
            main.py                    FastAPI app: routes, Pydantic validation, static hosting
            model_service.py           checksum verification, feature engineering, prediction
         model/
            lbw_model.joblib           frozen artefact, L2 logistic regression, feature set C
            lbw_model.sha256           integrity checksum, verified at startup
            model_params.json          exported coefficients and covariance for the interval
         static/
            index.html                 five screen prototype, no build step
         requirements.txt              pinned runtime dependencies
      designs/
         web/
            01-sign-up.png
            02-sign-in.png
            03-register.png
            04-visit-one.png
            05-visit-two.png
            06-assessment.png
            07-caseload.png
```

---

## 4. End to end walkthrough

### Step 1. Read the raw file

The raw CSV holds 8,817 rows and 683 columns. It is opened read only and its SHA-256 fingerprint is
recorded. Blood pressure is stored as text such as `119/65`, so it is split into a systolic and a
diastolic number. Values that are not physically possible are treated as missing rather than
deleted, so the row stays and only that one reading is set aside.

### Step 2. Build the study group

Each eligibility rule is applied in turn and counted, so the whole path can be checked.

| Step | Pregnancies | Removed |
| --- | --- | --- |
| All records in the file | 8,817 | 0 |
| Live birth, one baby, birth weight recorded | 8,161 | 656 |
| Both visits have usable pressure and weeks | 6,203 | 1,958 |
| Second visit later in pregnancy than the first | 6,065 | 138 |
| Both visits at or before 28 weeks (study group) | **3,908** | 2,157 |

Most of the drop is not poor data quality. It is the timing rule, because many pregnancies do not
have two usable early visits.

### Step 3. Apply the availability rule

A visit two measurement is used only if it was recorded for at least 60 percent of women.

- **Kept:** systolic pressure, diastolic pressure, weeks pregnant, weight, pulse.
- **Dropped:** breathing rate, body temperature, haemoglobin.

### Step 4. Build three nested feature sets

Set A sits inside set B, which sits inside set C. Because they are nested this way, any difference
in performance can only come from the extra information.

| Set | Contents | Features |
| --- | --- | --- |
| A | registration only | 13 |
| B | A plus visit two | 18 |
| C | A plus visit two plus change | 24 |

### Step 5. Experiment one, compare eight models

Eight well known models are run on feature set C on the same footing: logistic regression (L2 and
L1), linear discriminant, naive Bayes, nearest neighbours, decision tree, random forest, and
gradient boosted trees. They all cluster near the guessing level, so complexity buys nothing.

### Step 6. Experiment two, the main test

Does the score rise from A to B to C? The method is 5 fold stratified grouped cross validation,
grouped by registration profile, repeated 10 times, with an inner split choosing the
hyperparameters so the test part never influences the settings. Differences get a paired bootstrap
over 2,000 resamples. There is no oversampling and no class re weighting.

### Step 7. Supporting analyses

| Analysis | Figure |
| --- | --- |
| Calibration curve, can the probabilities be trusted | 9 |
| Coefficient weights, what the model leans on | 10 |
| Permutation importance, what the model really uses | 11 |
| Decision curve net benefit against send everyone and send no one | 12 |
| Smallest detectable gain, the study's own sensitivity | 13 |

One sealed hold out of 782 pregnancies and 41 cases is looked at exactly once.

### Step 8. Freeze the artefact

The chosen model is trained on the whole study group and written out as three files: the
`lbw_model.joblib` pipeline, the `lbw_model.sha256` checksum, and `model_params.json` holding the
exported coefficients. The artefact also carries the feature names, the medians, the cohort
probability distribution, the prevalence, and the frozen spec with the seed and the raw file
fingerprint.

### Step 9. Serve predictions two ways

| Path | How it runs | Notes |
| --- | --- | --- |
| **Server**, `POST /api/predict` | Loads the joblib file, verifies the checksum, runs the scikit-learn pipeline | This is the path that enforces integrity |
| **Browser**, `static/index.html` | Evaluates the exported linear coefficients client side | Works with no server and no connectivity |

Both paths return the identical probability, 95 percent interval, and percentile.

### Step 10. Order the caseload

Pregnancies are listed by predicted probability, giving a position rather than a clinical label.

### The 17 raw inputs

The caller supplies only what a health worker can collect. Everything else is derived by the
service, identically to the notebook.

| Group | Inputs |
| --- | --- |
| Mother | `age`, `height_cm`, `booking_weight` |
| History | `gravidity`, `prior_deliveries`, `prior_livebirths`, `prior_stillbirths`, `miscarriage_count` |
| Visit one | `ga_v1`, `sbp_v1`, `dbp_v1`, `weight_v1` |
| Visit two | `ga_v2`, `sbp_v2`, `dbp_v2`, `weight_v2`, `pulse_v2` |

Derived and never supplied: `miscarriage_any`, `d_sbp`, `d_dbp`, `d_ga`, `d_weight`,
`sbp_per_week`, `weight_per_week`. That gives **24 model features** in total.

---

## 5. Dataset

The study uses an antenatal care dataset collected in Tanzania. **The raw file is not committed to
this repository.** It is large and covered by its own licence from the original source.

### How to get it

1. Obtain the maternal antenatal dataset from its original source, the Mendeley Data record the
   study was benchmarked against.
2. Save the CSV in `antenatal-caseload-prediction/data/`, for example as `maternal_dataset.csv`.

### Point the notebook at your copy

Near the top of the notebook, in the cell under "Environment and how to run this notebook", one
line sets the path.

```python
RAW_PATH = '/mnt/user-data/uploads/maternal_dataset_csv__1_.csv'
```

Change it to your location.

```python
RAW_PATH = '../data/maternal_dataset.csv'
```

Then run from the top. The notebook records the file's SHA-256 fingerprint, so there is proof of
exactly which file produced the results. The committed run used a file whose digest begins
`ab95366ef22dde5d`.

### Privacy

Only use de identified data. Do not commit any file containing identifiable patient information.
The raw file is opened read only and is never written back to. Every correction is applied while
building features, not by editing the source.

---

## 6. Environment and setup

**Prerequisites:** Python 3.11 or newer. The committed run used Python 3.11.15.

The notebook and the web app have separate dependency sets. You can use one environment for both or
keep them apart. The pinned versions below are compatible.

### 6a. Clone

```bash
git clone https://github.com/Kelvin364/Antanental_risk_model.git
cd Antanental_risk_model/antenatal-caseload-prediction
```

### 6b. Notebook environment

```bash
cd notebook
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`notebook/requirements.txt`:

```
jupyter
nbformat
numpy
pandas
scikit-learn==1.8.0
matplotlib
seaborn
joblib
```

### 6c. Web app environment

```bash
cd webapp
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`webapp/requirements.txt`, pinned on purpose:

```
fastapi==0.142.2
uvicorn[standard]==0.46.0
pydantic==2.13.3
scikit-learn==1.8.0
joblib==1.5.3
numpy==2.4.4
```

> **scikit-learn and joblib must match the versions the artefact was built with**, 1.8.0 and 1.5.3.
> A different version may fail to deserialise `lbw_model.joblib`, or deserialise it subtly wrong.

### 6d. Exact versions of the committed run

| Component | Version |
| --- | --- |
| Python | 3.11.15 |
| NumPy | 2.4.4 |
| pandas | 3.0.2 |
| scikit-learn | 1.8.0 |
| matplotlib | 3.10.9 |
| seaborn | 0.13.2 |
| Random seed | `20260930` |

---

## 7. Running the notebook

Open it and run every cell from the top, or run it headlessly in one command.

```bash
cd antenatal-caseload-prediction/notebook
jupyter nbconvert --to notebook --execute --inplace Model-Notebook.ipynb
```

It needs no input along the way and finishes on an ordinary laptop in a few minutes.

The 14 sections:

| # | Section | What it does |
| --- | --- | --- |
| 1 | Requirements and tools | Maps each project requirement to how the notebook meets it, and justifies every tool |
| 2 | Environment and how to run | Prints versions and the seed, records the raw file's fingerprint |
| 3 | The fixed study plan | Every choice written down before any result was seen |
| 4 | Data engineering | Raw export to clean study group, each eligibility step counted (Figure 1), plus a consistency audit |
| 5 | Looking at the data | Outcome rarity (Figure 2), distributions by outcome (Figure 3), missingness (Figure 4), correlations (Figure 5) |
| 6 | Building the three feature sets | Nested sets A inside B inside C, grouping by registration profile |
| 7 | Experiment one | Eight models compared on set C (Figure 6), logistic regression chosen with reasons |
| 8 | Experiment two | The main test, repeated grouped CV plus paired bootstrap (Figures 7, 8, 9) |
| 9 | Which measurements carry signal | Coefficient weights (Figure 10) and permutation importance (Figure 11) |
| 10 | Is it useful for a real decision | Decision curve net benefit against send everyone and send no one (Figure 12) |
| 11 | How large an effect could be detected | Turns the paired comparison noise into a smallest detectable gain (Figure 13) |
| 12 | A single sealed test | The hold out, looked at exactly once |
| 13 | Saving the finished model | Trains on the whole group, writes the artefact and checksum |
| 14 | What we found, in plain words | Prints the conclusion straight from the numbers, so the words always match the result |

Section 13 writes the artefact to the notebook's output directory. To refresh the web app's copy,
move `lbw_model.joblib` and `lbw_model.sha256` into `webapp/model/` together. The server will
verify the new checksum on its next start.

---

## 8. Running the web application

```bash
cd antenatal-caseload-prediction/webapp
source .venv/bin/activate
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/**

On startup the server hashes `model/lbw_model.joblib` and compares it with
`model/lbw_model.sha256`. A mismatch **stops the server** with an explicit error, so the model
cannot be silently swapped.

Verify it is running.

```bash
curl http://127.0.0.1:8000/health
```

That returns the loaded model's checksum, feature count, cohort prevalence, and the frozen spec.

Try a prediction.

```bash
curl -X POST http://127.0.0.1:8000/api/predict \
  -H 'Content-Type: application/json' \
  -d '{
    "age": 24, "height_cm": 156, "booking_weight": 59,
    "gravidity": 2, "prior_deliveries": 1, "prior_livebirths": 1,
    "prior_stillbirths": 0, "miscarriage_count": 0,
    "ga_v1": 18, "sbp_v1": 110, "dbp_v1": 69, "weight_v1": 56,
    "ga_v2": 24, "sbp_v2": 112, "dbp_v2": 68, "weight_v2": 58, "pulse_v2": 78
  }'
```

The interface itself needs no build step and no bundler. `static/index.html` is a single file with
the model coefficients inlined, so it also runs offline on a low end device.

---

## 9. API reference

### `GET /health`

```json
{
  "status": "ok",
  "model_sha256": "b54f1c0c9d0e84e6a76267edd9c5ce412d06b12ab372c4fc4ca332e3b7d6cf81",
  "n_features": 24,
  "cohort_prevalence": 0.0527,
  "spec": {
    "outcome": "recorded birth weight below 2.5 kg",
    "prediction_moment": "second antenatal visit",
    "model": "logistic regression, feature set C",
    "class_weight": null,
    "oversampling": false,
    "seed": 20260930,
    "raw_sha256": "..."
  }
}
```

### `POST /api/predict`

**Body:** the 17 raw inputs listed in [section 4](#the-17-raw-inputs).

**Response:**

```json
{
  "probability": 0.1106,
  "interval_low": 0.0715,
  "interval_high": 0.1671,
  "cohort_percentile": 59.0,
  "prevalence": 0.0527
}
```

| Field | Meaning |
| --- | --- |
| `probability` | Calibrated probability of recorded low birth weight |
| `interval_low` and `interval_high` | 95 percent Wald interval on the logit, from the coefficient covariance |
| `cohort_percentile` | Where this pregnancy sits among the 3,908 study group predictions |
| `prevalence` | The cohort's natural rate, for context |

Enforced ranges. A violation returns HTTP **422** with a list of exactly what to fix.

| Field | Range | Field | Range |
| --- | --- | --- | --- |
| `age` | 12 to 55 | `ga_v1`, `ga_v2` | 1 to 28 weeks |
| `height_cm` | 120 to 210 | `sbp_v1`, `sbp_v2` | 60 to 250 mmHg |
| `booking_weight` | 30 to 150 kg | `dbp_v1`, `dbp_v2` | 30 to 160 mmHg |
| `gravidity` | 1 to 20 | `weight_v1`, `weight_v2` | 30 to 150 kg |
| `prior_deliveries`, `prior_livebirths`, `prior_stillbirths`, `miscarriage_count` | 0 to 20 | `pulse_v2` | 30 to 200 bpm |

Plus the study's timing rule. `ga_v2` must be strictly greater than `ga_v1`, and both at or before
28 weeks.

Interactive OpenAPI docs are at **http://127.0.0.1:8000/docs**

---

## 10. The interface: navigation and layout

A five step workflow with a persistent top app bar and a horizontal step navigator, mirroring the
real order of a home visit.

| # | Screen | Purpose | Layout |
| --- | --- | --- | --- |
| 1 | **Register** | Booking details known before visit two, mother plus pregnancy history | Two labelled field groups in a responsive grid |
| 2 | **Visit one** | Earlier visit, no laboratory measurements only | Single measurement group |
| 3 | **Visit two** | The prediction moment, shows the computed change since visit one | Measurement group plus read only derived fields |
| 4 | **Assessment** | Caseload position plus calibrated probability with interval | Two metric panels, a position bar, a plain language note |
| 5 | **Caseload** | All assessed pregnancies, ordered by probability | Sortable data table with position pills |

**Step 3, Visit two.** The computed change since visit one appears as read only fields, so the
health worker can see what the model is actually reacting to.

![Visit two screen](antenatal-caseload-prediction/designs/web/05-visit-two.png)

**Step 4, Assessment.** A position, a probability, and an interval. There is no clinical category
anywhere on this screen.

![Assessment screen](antenatal-caseload-prediction/designs/web/06-assessment.png)

### Navigation rules

- Steps unlock in order. A later step is reachable only once the earlier ones are complete and
  valid. The navigator disables unreachable steps and marks completed ones.
- **Caseload** is always reachable and is the default landing view, seeded with synthetic examples
  so the tool opens in a realistic working state.
- Every numeric field enforces its range on entry. **Run assessment** stays disabled until visit
  two is complete and the timing rule is satisfied.
- The layout is responsive to phone width, works in light and dark themes, and keeps a "synthetic
  data only" marker visible at all times.

### The two ways the model runs

- **In the browser**, `static/index.html` evaluates the exported linear coefficients client side,
  so the interface works with no server and no connectivity. This matches the field reality of a
  community health worker.
- **On the server**, `POST /api/predict` loads the same frozen artefact and runs it in Python.

Both paths return the identical probability, interval, and percentile. The server path is the one
that verifies the checksum.

---

## 11. Designs

All seven web screens are included as full resolution PNGs in `designs/web/`.

| File | Screen | In the prototype |
| --- | --- | --- |
| `web/01-sign-up.png` | Sign up | Design only, there is no auth in the prototype |
| `web/02-sign-in.png` | Sign in | Design only, there is no auth in the prototype |
| `web/03-register.png` | Register the pregnancy | Implemented |
| `web/04-visit-one.png` | First antenatal visit | Implemented |
| `web/05-visit-two.png` | Second antenatal visit, with the computed change | Implemented |
| `web/06-assessment.png` | Assessment, position and probability | Implemented |
| `web/07-caseload.png` | Caseload, ranked list | Implemented |

### 01. Sign up

![Sign up](antenatal-caseload-prediction/designs/web/01-sign-up.png)

### 02. Sign in

![Sign in](antenatal-caseload-prediction/designs/web/02-sign-in.png)

### 03. Register the pregnancy

![Register](antenatal-caseload-prediction/designs/web/03-register.png)

### 04. First antenatal visit

![Visit one](antenatal-caseload-prediction/designs/web/04-visit-one.png)

### 05. Second antenatal visit

![Visit two](antenatal-caseload-prediction/designs/web/05-visit-two.png)

### 06. Assessment

![Assessment](antenatal-caseload-prediction/designs/web/06-assessment.png)

### 07. Caseload

![Caseload](antenatal-caseload-prediction/designs/web/07-caseload.png)

### Design notes

- Green is used on the primary buttons and the active elements, meaning the active step, the
  position bar, and the priority pills.
- There is no logo mark.
- Step numbers and account initials are plain text, with no circle backgrounds.
- The primary typeface is Host Grotesk, with a monospace face for the figures.

### Editable Figma file

https://www.figma.com/design/UHmymjrnb2HJX47uQzf4jg

- Page **Web App** holds the seven web screens.
- Page **Mobile (reference)** holds an earlier phone sized version.

To let a reviewer open it, set the file to "Anyone with the link can view" from the Share menu.
Note that the Figma version still shows the number and initial circles. The PNGs in `web/` are the
current, refined designs.

---

## 12. Results in detail

### Experiment one, eight models on feature set C

Guessing level, PR AUC, is 0.053.

| Model | PR AUC | sd | ROC AUC | Brier | Calibration slope |
| --- | --- | --- | --- | --- | --- |
| Logistic regression (L2) | 0.079 | 0.002 | 0.602 | 0.050 | 0.60 |
| Random forest | 0.079 | 0.005 | 0.619 | 0.050 | 1.24 |
| Gradient boosted trees | 0.078 | 0.004 | 0.605 | 0.050 | 0.78 |
| Logistic regression (L1) | 0.078 | 0.002 | 0.601 | 0.050 | 0.61 |
| Linear discriminant | 0.076 | 0.002 | 0.599 | 0.050 | 0.54 |
| Nearest neighbours (25) | 0.066 | 0.003 | 0.537 | 0.051 | 0.02 |
| Naive Bayes | 0.065 | 0.002 | 0.573 | 0.084 | 0.04 |
| Decision tree | 0.062 | 0.003 | 0.559 | 0.051 | 0.19 |

Every model sits close to the guessing line and they cluster together. The point is not that one
wins. It is that the complex models do not beat the simple one in any way that matters.

### Experiment two, the main test

Repeated 10 times, 5 fold grouped cross validation, with an inner split for hyperparameters.

| Model | Features | PR AUC | sd | ROC AUC | Brier | Calibration slope |
| --- | --- | --- | --- | --- | --- | --- |
| Logistic regression | A registration | 0.073 | 0.004 | 0.559 | 0.052 | 0.378 |
| Logistic regression | B plus visit two | 0.074 | 0.003 | 0.572 | 0.052 | 0.504 |
| Logistic regression | C plus change | 0.074 | 0.004 | 0.577 | 0.051 | 0.436 |
| Gradient boosted trees | A registration | 0.073 | 0.005 | 0.578 | 0.050 | 0.561 |
| Gradient boosted trees | B plus visit two | 0.076 | 0.007 | 0.600 | 0.050 | 0.632 |
| Gradient boosted trees | C plus change | 0.075 | 0.006 | 0.597 | 0.050 | 0.625 |

Paired bootstrap on the differences. **Every interval includes zero**, for both models and both
metrics.

| Model | Comparison | Metric | Change | 95 percent interval |
| --- | --- | --- | --- | --- |
| Logistic regression | B over A | PR AUC | plus 0.002 | minus 0.014 to plus 0.014 |
| Logistic regression | B over A | ROC AUC | plus 0.011 | minus 0.018 to plus 0.040 |
| Logistic regression | C over B | PR AUC | minus 0.001 | minus 0.007 to plus 0.005 |
| Logistic regression | C over B | ROC AUC | plus 0.010 | minus 0.006 to plus 0.027 |
| Logistic regression | C over A | PR AUC | plus 0.001 | minus 0.016 to plus 0.014 |
| Logistic regression | C over A | ROC AUC | plus 0.021 | minus 0.008 to plus 0.050 |
| Gradient boosted trees | B over A | PR AUC | plus 0.004 | minus 0.007 to plus 0.013 |
| Gradient boosted trees | B over A | ROC AUC | plus 0.024 | minus 0.003 to plus 0.051 |
| Gradient boosted trees | C over B | PR AUC | minus 0.001 | minus 0.006 to plus 0.005 |
| Gradient boosted trees | C over B | ROC AUC | plus 0.002 | minus 0.012 to plus 0.016 |
| Gradient boosted trees | C over A | PR AUC | plus 0.003 | minus 0.009 to plus 0.013 |
| Gradient boosted trees | C over A | ROC AUC | plus 0.026 | minus 0.003 to plus 0.055 |

### How large an effect the study could detect

| Model | Metric | Gain observed | Noise (SE) | Smallest detectable gain |
| --- | --- | --- | --- | --- |
| Logistic regression | PR AUC | 0.001 | 0.007 | **0.020** |
| Logistic regression | ROC AUC | 0.021 | 0.015 | **0.041** |
| Gradient boosted trees | PR AUC | 0.003 | 0.006 | **0.015** |
| Gradient boosted trees | ROC AUC | 0.026 | 0.015 | **0.042** |

The observed gains are far below what the study could catch. This is the key fairness check on a
null result, because it reports its own sensitivity rather than claiming more than it can see.

### Which measurements actually carry signal

Top six by permutation importance, the fall in PR AUC when scrambled.

| Feature | Drop |
| --- | --- |
| `gravidity` | 0.0096 |
| `sbp_v1` | 0.0081 |
| `pulse_v2` | 0.0075 |
| `booking_weight` | 0.0073 |
| `prior_livebirths` | 0.0067 |
| `weight_v2` | 0.0060 |

Note that the two strongest are registration variables, which is consistent with the headline
result.

### The sealed hold out

The development part held 3,126 pregnancies and 165 cases. The sealed part held 782 pregnancies and
41 cases. Guessing level on the sealed part was 0.052.

| Model | Features | PR AUC | ROC AUC |
| --- | --- | --- | --- |
| Logistic regression | A registration | 0.077 | 0.530 |
| Logistic regression | B plus visit two | 0.079 | 0.549 |
| Logistic regression | C plus change | 0.083 | 0.547 |
| Gradient boosted trees | A registration | 0.059 | 0.505 |
| Gradient boosted trees | B plus visit two | 0.063 | 0.547 |
| Gradient boosted trees | C plus change | 0.063 | 0.527 |

With only 41 cases this is a rough check on direction, not a precise measurement, and it was looked
at exactly once.

### Data consistency audit

Three field pairs in the raw file can contradict each other. They are reported rather than silently
fixed, and handled by trusting the measured number over the stored flag.

| Check | Records affected in the whole file | How it is handled |
| --- | --- | --- |
| Miscarriage yes or no disagrees with the miscarriage count | 15 | The feature uses the count and derives its own yes or no |
| Four kilogram flag disagrees with the measured birth weight | 25 | The outcome uses the measured kilograms, the flag is ignored |
| More prior live births than total pregnancies | 3,080 | Counts of prior births are used directly, not any single stored field |

---

## 13. Design decisions and why

### Why logistic regression is the main model

1. **Nothing is given up.** Its score matches the tree based models and the rest.
2. **Its probabilities can be trusted at face value**, which matters because the interface shows a
   probability. Several alternatives give far less trustworthy probabilities, with nearest
   neighbours at a 0.02 calibration slope and naive Bayes at 0.04.
3. **It can be written down as a formula**, so a clinician can see exactly what drives a
   prediction. That openness is worth more than a fraction of a point no model reaches anyway.
4. **It behaves well when the outcome is rare**, which is the situation here.

Gradient boosted trees are kept throughout as a second opinion, confirming the conclusion does not
depend on the model choice.

### Why no deep learning

With about 206 low birth weight cases there is not enough signal to train a neural network
honestly. Simpler models are the correct choice at this size.

### Why no oversampling and no class weighting

Both inflate apparent performance and distort the predicted probabilities. Since the interface
shows a probability and a position, the probabilities must stay honest. This is the main
methodological difference from several earlier studies on similar data.

### Why grouped splits

Splits are grouped by registration profile, 3,905 distinct profiles with 3 shared by more than one
pregnancy, so a near duplicate of a training record cannot land in the test part.

### Why PR AUC is the main score

The outcome occurs in 5.27 percent of pregnancies. On a rare outcome, PR AUC reflects whether the
few real cases land near the top of a ranked list, which is precisely the decision the tool
supports. ROC AUC, Brier score, and calibration slope are reported alongside it.

### Tooling choices

| Layer | Tool | Reason |
| --- | --- | --- |
| Language | Python 3.11 | Standard for this work, already on the course machines |
| Data | pandas | Handles a wide 683 column export cleanly |
| Numerics | NumPy | Fast array maths the rest builds on |
| Models | scikit-learn 1.8.0 | Established, documented library for traditional models |
| Figures | matplotlib and seaborn | Full control over clear, readable charts |
| Persistence | joblib 1.5.3 | The standard way to store a scikit-learn pipeline |
| Document | Jupyter | Explanation, code, and results in one document |
| API | FastAPI and Uvicorn | Typed Pydantic validation, automatic OpenAPI docs, minimal footprint |
| Interface | Single page HTML, CSS, and JS with no build step | Runs offline on a low end device |
| Integrity | SHA-256 | The server refuses to start if the artefact changed |

---

## 14. Reproducibility and integrity

- **One fixed seed.** `RANDOM_STATE = 20260930` drives every random step, so the same run always
  gives the same numbers.
- **The raw file is opened read only** and its SHA-256 is recorded in the notebook output and
  embedded in the artefact's spec, so there is proof the analysis ran on the file we think it did.
- **The study plan was fixed in advance**, in notebook section 3. The outcome, timing rule, feature
  sets, availability rule, split strategy, main metric, and the no oversampling rule were all
  written down before any result was seen.
- **The artefact is checksummed.** `lbw_model.sha256` holds
  `b54f1c0c9d0e84e6a76267edd9c5ce412d06b12ab372c4fc4ca332e3b7d6cf81`. The server hashes the file at
  startup and refuses to load a mismatch.
- **The service never trains.** It deserialises one frozen pipeline and runs it. Feature
  engineering in `model_service.py` is a line for line mirror of the notebook's.
- **Both execution paths agree.** The browser's client side evaluation of the exported coefficients
  and the server's scikit-learn pipeline return identical probabilities, intervals, and
  percentiles.
- **The conclusion is generated from the numbers.** Notebook section 14 prints it, so the prose can
  never drift away from the result.

---

## 15. Scope, limitations, and safety

- **This is not a medical device and not for clinical use.** All example pregnancies in the
  prototype are synthetic and were generated for the demo.
- **The output is a position for ordering visits and a calibrated probability, never a clinical
  category.** A higher position is a prompt to look sooner, not a diagnosis.
- **The study's headline finding is a null result.** The measured incremental value of the second
  visit over registration data alone is small and not statistically distinguishable from zero at
  this event count. The prototype is a packaging demonstration, not a claim of clinical utility.
- **Discrimination is weak in absolute terms.** ROC AUC is about 0.58 and PR AUC about 0.074
  against a 0.053 guessing level. It beats guessing, but it is not a strong predictor.
- **Generalisability is untested.** One Tanzanian cohort, 3,908 pregnancies, 206 events, and no
  external validation.
- **The 28 week ceiling and the two visit requirement** remove 2,295 otherwise eligible
  pregnancies. The study group is therefore women with two usable early visits, not all
  pregnancies.
- **Haemoglobin at visit two was excluded** by the 60 percent availability rule. A laboratory value
  that might carry signal is simply not recorded often enough to use.
- **No authentication.** The sign up and sign in screens exist in the designs only. The prototype
  has no accounts, no persistence, and no access control, so it is not deployment ready.

---

## 16. Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| Server exits with "Model checksum mismatch" | `lbw_model.joblib` changed. Restore the committed artefact, or regenerate both the artefact and `lbw_model.sha256` from notebook section 13 together. |
| Server exits with "Model artefact or checksum missing" | Run uvicorn from the `webapp/` directory. Paths resolve relative to the package, and both files must be in `webapp/model/`. |
| `joblib.load` raises an unpickling or attribute error | scikit-learn version mismatch. Install exactly `scikit-learn==1.8.0` and `joblib==1.5.3`. |
| Notebook fails on the first data cell | `RAW_PATH` still points at the original upload location. Set it to your copy, see [section 5](#5-dataset). |
| `POST /api/predict` returns 422 | Read the `detail` list. It names each missing field, each out of range field with its allowed bounds, and the timing rule if `ga_v2` is not later than `ga_v1`. |
| "Run assessment" stays disabled in the interface | Visit two is incomplete or the timing rule is unsatisfied. `ga_v2` must be strictly greater than `ga_v1`, and both at or before 28 weeks. |
| Figures are missing after a fresh run | Run every cell from the top. Later cells depend on names defined earlier. |

---

## 17. Sources

- Collins, G. S., and others (2024). TRIPOD plus AI statement: updated guidance for reporting
  clinical prediction models. BMJ, 385, e078378.
- Saito, T., and Rehmsmeier, M. (2015). The precision recall plot is more informative than the ROC
  plot on imbalanced datasets. PLOS ONE, 10(3), e0118432.
- Van Calster, B., and others (2019). Calibration: the Achilles heel of predictive analytics. BMC
  Medicine, 17, 230.
- Vickers, A. J., and Elkin, E. B. (2006). Decision curve analysis: a new method for evaluating
  prediction models. Medical Decision Making, 26(6), 565 to 574.

---

## 18. Licence

MIT. See [`antenatal-caseload-prediction/LICENSE`](antenatal-caseload-prediction/LICENSE).
Copyright (c) 2026 Kelvin Rwihimba.

The raw antenatal dataset is not covered by this licence and is not distributed here. It remains
under the terms of its original source.
