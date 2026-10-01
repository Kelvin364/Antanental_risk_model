# Data

The study uses an antenatal care dataset collected in Tanzania. The raw file is **not
committed** to this repository, because it is large and is covered by its own licence from the
original source.

## How to get it

1. Obtain the maternal antenatal dataset from its original source (the Mendeley Data record the
   study was benchmarked against).
2. Save the CSV file in this `data/` folder, for example as `maternal_dataset.csv`.

## Point the notebook at it

The notebook reads the file from a single path near the top, in the cell under
"Environment and how to run this notebook":

```python
RAW_PATH = '/mnt/user-data/uploads/maternal_dataset_csv__1_.csv'
```

Change that line to the location of your copy, for example:

```python
RAW_PATH = '../data/maternal_dataset.csv'
```

Then run the notebook from the top. The notebook records the file's fingerprint (a SHA-256
hash) so there is proof of exactly which file produced the results.

## A note on privacy

Only use de identified data. Do not commit any file that contains identifiable patient
information. The `.gitignore` already excludes CSV files to prevent this by accident.
