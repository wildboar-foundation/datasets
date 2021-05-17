# Monash, UEA & UCR Time Series Regression Datasets

## Dataset information

- Number of datasets: 19
- Number of dimensions: 1-24
- Source: http://tseregression.org

## Build instructions

    > CB_DATASET_FILE=dataset.zip CB_RESULT_DIR=npz python create_bundle.py
    > zip default.zip -r --junk-paths npz/
    > sha1sum default.zip

