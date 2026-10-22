# Architecture

The repository has two parts that share one package. The research pipeline in
`src/antenatal` turns the released file into results and a frozen artefact.
The prototype in `webapp/` loads that artefact and scores synthetic cases with
it. The prototype never trains and never repeats a calculation of its own:
feature construction, the probability, the interval and the rank all come from
the package.

## Modules

```mermaid
flowchart LR
    subgraph pipeline["Research pipeline: src/antenatal"]
        config["config<br/>StudySpec, ranges, seed"]
        data["data<br/>DataLoader, parsers, dictionary"]
        audit["audit<br/>quality, missingness"]
        cohort["cohort<br/>RecordCleaner, CohortBuilder, PartitionWriter"]
        features["features<br/>AvailabilityScreen, FeatureSet A B C, FeatureBuilder"]
        models["models<br/>ModelFactory"]
        evaluation["evaluation<br/>NestedCVRunner, metrics, GroupBootstrap,<br/>comparisons, sensitivity, HoldoutEvaluator"]
        artefact["artefact<br/>FittedPipelineArtefact, Wald interval"]
        reporting["reporting<br/>figures, manifest, results summary, README blocks"]
        cli["cli<br/>python -m antenatal"]
        storage["storage<br/>research tables, load-db"]
    end
    subgraph files["Files"]
        raw[("data/maternal_dataset_csv.csv")]
        parts[("partitions/<br/>holdout_ids.csv, folds.parquet")]
        outs[("outputs/<br/>tables, figures, manifest")]
        model[("webapp/model/<br/>lbw_model.joblib, sha256, version.json")]
    end
    subgraph app["Prototype: webapp/app"]
        api["api<br/>health, predict, cases"]
        services["services<br/>validation, CaseService, ModelService, RankingService"]
        db[("SQLite<br/>synthetic cases, visits, assessments;<br/>research tables from load-db")]
    end
    subgraph ui["Interface: frontend"]
        page["Next.js static export<br/>five screens, typed client from openapi.json"]
    end

    raw --> data --> cohort
    config --> cohort & features & models & evaluation
    cohort --> parts
    cohort --> features --> evaluation
    models --> evaluation
    evaluation --> reporting --> outs
    evaluation --> artefact --> model
    cli --> cohort & evaluation & artefact & reporting
    audit --> outs
    page --> api --> services
    services --> db
    outs --> storage --> db
    cli --> storage
    model --> services
    services -. "imports FittedPipelineArtefact and FeatureBuilder" .-> artefact
```

Each package has one job, and none reaches into another's internals:

| Package | Responsibility |
| --- | --- |
| `config` | The frozen `StudySpec`: every constant, range and seed. Sensitivity analyses are copies with one field changed |
| `data` | Reading the file after its checksum is verified, and pure parsers for blood pressure, numbers and yes or no fields |
| `audit` | Data quality findings and missingness summaries |
| `cohort` | Cleaning, the eligibility steps of Table 3.5 with an exclusion reason per record, the sealed partition and the outer folds |
| `features` | The outcome blind availability screen and the nested feature sets, chosen per model family by polymorphic `FeatureSet.columns` |
| `models` | Construction of every pipeline: missing value treatment, scaling, estimator and tuning grid |
| `evaluation` | Nested cross validation, metric strategies, paired group bootstrap, detectable difference, sensitivity and extension analyses, and the only gate to the held out partition |
| `artefact` | The fitted development pipeline with its covariance, reference probabilities, checksum and version |
| `reporting` | Figures, the manifest, the results summary and the generated README blocks |
| `storage` | The research side of the data model in SQLite, written by `load-db` |

## Data model

The proposal's data model (Section 3.4.4) has a research side and an interface side. Both live in the application's SQLite file, `webapp/data/app.sqlite3`, which is created locally and not committed.

| Table | Entity | Written by | Uniqueness |
| --- | --- | --- | --- |
| `pregnancy_records` | PREGNANCY_RECORD | `load-db`, from `outputs/cohort_manifest.csv` | one row per record |
| `visit_measurements` | VISIT_MEASUREMENT | `load-db`, cleaned visit one and two values | record and visit number |
| `model_configurations` | MODEL_CONFIGURATION and PIPELINE_ARTEFACT | `load-db`, from each `version.json` and `model_params.json` | version |
| `evaluation_results` | EVALUATION_RESULT | `load-db`, from `outputs/tables/cv_fold_metrics.csv` | model, feature set, repeat and fold |
| `synthetic_cases` | SYNTHETIC_CASE | the prototype | synthetic flag always true |
| `synthetic_visits` | SYNTHETIC_VISIT | the prototype | case and visit number |
| `assessments` | ASSESSMENT | the prototype | references the artefact version and checksum |

Exclusion reasons are columns of `pregnancy_records` (EXCLUSION_LOG), and partition assignments stay in `partitions/` (PARTITION_ASSIGNMENT), so no table records which records are held out. `load-db` drops and rebuilds its four tables, so it can be repeated.

In the prototype, routers validate and route, services decide, the package
computes, and the database stores.

## Request flow for one assessment

A synthetic case is registered, its two visits are recorded, and an assessment is requested.

```mermaid
sequenceDiagram
    actor User
    participant Page as Next.js interface
    participant API as api/cases.py
    participant Rules as services/validation.py
    participant Cases as services/case_service.py
    participant Model as services/model_service.py
    participant Artefact as FittedPipelineArtefact
    participant DB as SQLite

    User->>Page: Register (synthetic flag locked on)
    Page->>API: POST /api/cases
    API->>Cases: create(payload)
    Cases->>Rules: check_case: synthetic flag, cleaning ranges
    alt flag missing or value out of range
        Rules-->>Page: 422 with one message per field
    else accepted
        Cases->>DB: insert synthetic case
        Cases-->>Page: 201 case
    end
    User->>Page: Visit one, then visit two
    Page->>API: PUT /api/cases/{id}/visits/{1 or 2}
    API->>Cases: save_visit
    Cases->>Rules: check_visit: ranges, at or before 28 weeks, visit two later than visit one
    alt rule broken
        Rules-->>Page: 422 with the rule
    else accepted
        Cases->>DB: insert or replace the visit
    end
    Page->>API: POST /api/cases/{id}/assessment
    API->>Cases: assess
    Cases->>Model: predict(study values)
    Model->>Artefact: assess(case)
    Note over Artefact: FeatureBuilder derives the columns,<br/>the fitted pipeline gives the probability,<br/>the coefficient covariance gives the Wald interval,<br/>the reference probabilities give the rank
    Artefact-->>Model: probability, interval, rank
    Cases->>DB: store with artefact version, checksum and reference size
    Cases-->>Page: 201 assessment with limitation text
    Page-->>User: rank, probability, interval, prevalence, events, artefact version
```

Before any of this, the application factory in `webapp/app/main.py` creates
`ModelService`, which verifies the artefact's SHA 256. If the file has
changed, `ChecksumMismatch` is raised and the server does not start.

## Analysis flow

```mermaid
flowchart TD
    A["derive-cohort<br/>released file to the analysis cohort"] --> B["seal-partition<br/>held out identifiers written once with a checksum"]
    B --> C["run-analysis<br/>nested grouped cross validation on development records"]
    C --> D["run-extensions<br/>further analyses on the same folds"]
    C --> E["freeze-artefact<br/>one fit on development records"]
    E --> F["webapp loads the artefact"]
    B -. "opened only by HoldoutEvaluator, after supervisor review" .-> G["evaluate the held out partition once (Stage 4, not run)"]
```

The counts on each step are in `outputs/tables/cohort_flow.csv`.
