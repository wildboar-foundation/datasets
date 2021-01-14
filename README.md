# UCR Time series repository

## Dataset information

- Number of datasets: 128
- Number of dimensions: 1
- Source: http://timeseriesclassification.com

## Build instructions

    > CB_DATASET_FILE=dataset.zip CB_RESULT_DIR=npy python create_bundle.py
    > CB_DATASET_FILE=dataset.zip CB_RESULT_DIR=npy-no-missing CB_NO_MISSING=1 python create_bundle.py
    > zip default.zip -r --junk-paths npy/
    > zip no-missing.zip -r --junk-paths npy-no-missing/
    > sha1sum default.zip
    > sha1sum no-missing.zip


