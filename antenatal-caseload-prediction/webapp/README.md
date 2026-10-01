# Antenatal Caseload Prototype — Initial Software Demo

A research prototype interface for the capstone study *"Incremental value of two
antenatal measurements for predicting recorded low birth weight in a Tanzanian
cohort."* It lets a user register a pregnancy, enter two antenatal visits, and
receive a **caseload position** and a **calibrated probability of low birth
weight** with a 95% interval — computed by the frozen model from the
accompanying notebook.

> **Synthetic data only. Not a medical device and not for clinical use.**
> The interface exists to demonstrate how the study's model would be packaged
> for a community health worker; it makes no care decisions and shows no
> clinical risk category.

---

## 1. Requirements and tools

### What the demo does
- Collects the raw inputs a health worker can obtain without a laboratory,
  across five screens: **Register → Visit one → Visit two → Assessment → Caseload**.
- Enforces physiological ranges on every field and the study's timing rule
  (visit-2 gestational age must be later than visit-1, both within 28 weeks).
- Loads the **frozen model only from a checksum-verified serialised artefact**;
  it never retrains.
- Returns a probability, a 95% interval, and a percentile position within the
  study cohort so pregnancies can be ordered by who to see first.

### Tools and why each was chosen
| Layer | Tool | Reason |
| --- | --- | --- |
| Model | scikit-learn 1.8.0 + joblib | The artefact is a scikit-learn pipeline; the loader version must match the trainer to deserialise safely |
| API | FastAPI + Uvicorn | Typed request validation via Pydantic, automatic OpenAPI docs, minimal footprint |
| Interface | Single-page HTML/CSS/JS (no build step) | Runs offline on a low-end device; the same page the browser prototype uses |
| Integrity | SHA-256 checksum | The server refuses to start if the model artefact has changed |

### Inputs the model consumes
Seventeen raw inputs (registration + two visits). The remaining features
(miscarriage flag, visit-to-visit changes, weekly rates of change) are
**derived** by the service, identically to the notebook — the caller never
supplies them.

---

## 2. Development environment setup

**Prerequisites:** Python 3.11 or newer.

```bash
# 1. From the webapp/ directory, create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload

# 4. Open the interface
#    http://127.0.0.1:8000/
```

On startup the server verifies `model/lbw_model.joblib` against
`model/lbw_model.sha256`. A mismatch stops the server with a clear error — the
model cannot be silently swapped.

**Verify it is running:**
```bash
curl http://127.0.0.1:8000/health
```
returns the loaded model's checksum, feature count, cohort prevalence, and the
frozen specification. Interactive API docs are served at
`http://127.0.0.1:8000/docs`.

### Project layout
```
webapp/
├── app/
│   ├── main.py            FastAPI app: routes, validation, static hosting
│   └── model_service.py   Checksum verification, feature engineering, prediction
├── model/
│   ├── lbw_model.joblib   Frozen serialised model (logistic regression, set C)
│   ├── lbw_model.sha256   Integrity checksum, verified on startup
│   └── model_params.json  Exported coefficients (used for the 95% interval)
├── static/
│   └── index.html         The five-screen prototype interface
├── requirements.txt       Pinned dependencies
└── README.md
```

---

## 3. Navigation and layout structures

The interface is a **five-step workflow** with a persistent top app bar and a
horizontal step navigator. It mirrors the real order of a home visit.

| # | Screen | Purpose | Layout |
| --- | --- | --- | --- |
| 1 | **Register** | Booking details known before visit 2 (mother + pregnancy history) | Two labelled field groups in a responsive grid |
| 2 | **Visit one** | Earlier visit; no-laboratory measurements | Single measurement group |
| 3 | **Visit two** | The prediction moment; shows computed change since visit 1 | Measurement group + read-only derived fields |
| 4 | **Assessment** | Caseload position + calibrated probability with interval | Two metric panels, a position bar, and a plain-language note |
| 5 | **Caseload** | All assessed pregnancies, ordered by probability | Sortable data table with position pills |

**Navigation rules**
- Steps unlock in order: a later step is reachable only once the earlier ones
  are complete and valid. The step navigator disables steps that cannot yet be
  reached and marks completed ones.
- The **Caseload** screen is always reachable and is the default landing view,
  seeded with synthetic examples so the tool opens in a realistic working state.
- Every numeric field enforces its range on entry; the "Run assessment" action
  stays disabled until visit two is complete and the timing rule is satisfied.
- The layout is responsive to phone width, works in light and dark themes, and
  keeps a "synthetic data only" marker visible at all times.

### The two ways the model runs
- **In the browser** (`static/index.html`): the exported linear coefficients
  are evaluated client-side, so the interface works with no server and no
  connectivity — matching the field reality of a community health worker.
- **On the server** (`POST /api/predict`): the same frozen artefact is loaded
  and run in Python. Both paths return the identical probability, interval, and
  percentile; the server path is the one that verifies the checksum.

---

## API reference

`GET /health` → status, model checksum, feature count, prevalence, spec.

`POST /api/predict` → body of 17 raw inputs; returns:
```json
{
  "probability": 0.1106,
  "interval_low": 0.0715,
  "interval_high": 0.1671,
  "cohort_percentile": 59.0,
  "prevalence": 0.0527
}
```
Out-of-range or missing fields, or a visit-2 gestational age not later than
visit-1, return HTTP 422 with a list of what to fix.

---

## Scope and safety notes
- The output is a **position for ordering visits and a calibrated probability**,
  never a clinical category. A higher position is a prompt to look sooner, not a
  diagnosis.
- The model is the frozen primary model from the notebook (L2 logistic
  regression, feature set C). Its measured incremental value over registration
  data alone is small and not statistically distinguishable from zero at this
  event count; the notebook reports this in full. The prototype is a packaging
  demonstration, not a claim of clinical utility.
- All example pregnancies are synthetic and were generated for this demo.
