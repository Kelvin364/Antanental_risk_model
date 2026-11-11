# Register of further analyses

This repository keeps two models: the served 28 week model (the main study, `src/antenatal` and `webapp/model`) and the week 36 model (`week36_model`). Seven further analyses were run on development records between 8 and 11 November 2026 to test whether either model could be improved or combined. None changed a conclusion, so their code was removed from the working tree to keep it readable.

None of them is hidden. Every one had its plan committed before any result was computed, and all of their code, outputs and reports remain in git under the tag `archive-all-analyses-2026-11-11`, in the folder `lbw_detection_track/`. To restore one:

```
git checkout archive-all-analyses-2026-11-11 -- lbw_detection_track/<folder>
```

No analysis below opened the main study's held out partition or the week 36 test set. All results are internal validation: grouped repeated cross validation on development records, with 95 percent intervals from 2,000 resamples of whole registration groups.

| Folder | Question | Plan commit | Result |
| --- | --- | --- | --- |
| `target_study` | Can routine records reach ROC AUC 0.80 with any of 37 model and predictor combinations, up to 234 inputs? | d04e37f | No. Best ROC AUC 0.669 (0.624 to 0.713), random forest on every usable column |
| `fusion` | Does combining the served model with the week 36 model rank cases better? | b3a5a3b | No. Stacked combination against the served model on average precision: +0.0003 (−0.0158 to +0.0146) |
| `clinical_redesign` | Why is the ceiling low, and what data would a stronger study need? | 8e6e930 | No model fitted. The file lacks fetal growth measures, delivery dates and reliable obstetric history; plan for a future study |
| `sequential` | Does a second look at 36 weeks add to the served model's 28 week flags? | d670883 | No. Against lowering the served threshold to the same workload: −2.4 points of sensitivity (−5.1 to +0.3) |
| `whole_pregnancy` | Does a summary of every visit up to 36 weeks improve the week 36 model? | e561457 | No. Every visit against the latest visit only: +0.011 ROC AUC (−0.024 to +0.047) |
| `follow_up` | Does incomplete follow up at either end of the collection period blur the signal? | 6561210 | No. Complete follow up lowered ROC AUC in all 8 configurations. The low birth weight share does change with calendar start: 1.5 to 1.9 percent for pregnancies starting in 2023, 6.4 percent for late 2024. This is reported as a limitation |
| `continuous` | Does predicting the birth weight itself, then ranking by it, beat the yes or no classifiers? | a264373 | No. Primary comparison: −0.001 ROC AUC (−0.037 to +0.035) |

Each folder holds a `PROTOCOL.md` committed before its results, a `REPORT.md`, the code and an `outputs/` folder. The reports give every number with its source file.
