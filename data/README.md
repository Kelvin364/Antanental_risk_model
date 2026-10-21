# Data

`maternal_dataset_csv.csv` is version 1 of the Dataset for Maternal Health Risks
Stratification (MHRS) in Tanzania.

| Item | Value |
| --- | --- |
| Producers | University of Dodoma (Mwifunyi et al., 2025) |
| DOI | https://doi.org/10.5281/zenodo.15309733 |
| Licence | Creative Commons Attribution 4.0 (CC BY 4.0) |
| Records | 8,817, one per pregnancy |
| Columns | 683 |
| SHA 256 | `ab95366ef22dde5d13df93f10723942f5faffda8fbf0007e8efe85e4f25c1126` |

The file is redistributed here under the terms of its licence, unchanged. The
pipeline opens it for reading only, verifies the SHA 256 above before parsing,
and stops with `ChecksumMismatch` if the file differs by a single byte.

## Fetching it again

1. Download `maternal_dataset_csv.csv` from the Zenodo record above.
2. Save it in this folder under the same name.
3. Check it: `shasum -a 256 data/maternal_dataset_csv.csv` must print the digest above.

The official data dictionary is `metadata.pdf` on the same Zenodo record. Where
it and this repository disagree about what a field means, the dictionary wins.

Citation: Mwifunyi, R., Kibinda, N., Elisa, N., Rashidi, F. U., Hassan, K.,
Mohsini, M., Masoi, T., Mnabwiru, L., Hussein, Y., and Manangwa, S. (2025).
Dataset for maternal health risks stratification (MHRS) in Tanzania (Version 1)
[Data set]. Zenodo. https://doi.org/10.5281/zenodo.15309733
