# Ethics note

This note records what is known about the ethical basis of the data this
study reuses, what could not be found, and the status of the optional
walkthrough. It answers TRIPOD+AI item 17 as far as the sources allow.

## Dataset

| Item | Value | Source |
| --- | --- | --- |
| Title | Dataset for Maternal Health Risks Stratification (MHRS) in Tanzania | Zenodo record 15309733 |
| Authors | Mwifunyi, R., Kibinda, N., Elisa, N., Rashidi, F. U., Hassan, K., Mohsini, M., Masoi, T., Mnabwiru, L., Hussein, Y., and Manangwa, S. | Zenodo record 15309733 |
| Version used | Version 1, published 30 April 2025 | Zenodo record 15309733 |
| File used | `maternal_dataset_csv.csv`, SHA 256 recorded in `data/README.md` and verified on every load | This repository |
| Newer version | The record states that a newer version exists. This study uses version 1 only, fixed by its checksum | Zenodo record 15309733 |
| Licence | Creative Commons Attribution 4.0 International | Zenodo record 15309733 |
| Funders named on the record | Wellcome Trust; Lacuna Fund, grant 228079 | Zenodo record 15309733 |
| Collection period | 20 May 2024 to 30 March 2025 | Zenodo record 15309733 |
| Setting | Pregnant women attending maternity primary health facilities in Chamwino, Mkuranga, Meatu, Mbulu and Kilolo districts | Zenodo record 15309733 |
| DOI | https://doi.org/10.5281/zenodo.15309733 | |

## Ethics approval and consent statements of the data producers

> **PLACEHOLDER: no statement found yet.** The Zenodo record page
> (https://zenodo.org/records/15309733) and its `metadata.pdf`, a field
> dictionary, were read on 21 October 2026. Neither contains a statement on
> ethical approval, the approving committee, a permit or reference number,
> informed consent, or de-identification. The record links no data paper.
> No wording has been paraphrased or reconstructed here. When the producers'
> statement is obtained, quote it here exactly, with the document and page or
> section.

## Gaps found

1. **No published ethics or consent statement.** The release does not state which body approved the original collection or how consent was obtained. Reuse here rests on the CC BY 4.0 licence and on the data containing no direct identifiers.
2. **Identifiers.** The file has no names, facility identifiers or geographic coordinates. It does hold exact dates (last menstrual period, expected delivery) and registration details. Records that share age, last menstrual date, height, weight and prior deliveries are grouped in the analysis, and only a short hash of that key is published in `outputs/cohort_manifest.csv`.
3. **Suspect fields.** The data audit found history fields that agree with delivery outcomes far more than real history should. They are excluded as predictors pending clarification from the publisher (proposal Table 3.3).
4. **University determination.** The proposal states that the study follows the university's decision on secondary data ethics and claims no exemption. That decision is to be recorded here when it is received.

## Use of the data in this study

* The raw file is opened for reading only and never modified. Its SHA 256 is verified before every load.
* No attempt is made to re-identify anyone, and the data are not linked to any other source.
* No output informs the care of any pregnant woman. The prototype accepts synthetic cases only, refuses to save a case without the synthetic flag, and states this on every screen.

## Walkthrough with health workers

A walkthrough of the prototype with two or three health workers or clinicians,
using synthetic cases only, is a **proposed activity** (proposal Sections 1.5
and 3.6). It has **not taken place**. It is pending the African Leadership
University's determination, and it will not start before that determination
is received and recorded here. It is not on the critical path of the study and
is not a clinical evaluation.
