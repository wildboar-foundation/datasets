# Time series outlier detection

## Dataset information

- Number of datasets: 128
- Number of dimensions: 1
- Source: http://timeseriesclassification.com

These datasets are constructed using the `EmmottLabler` with ~5% outliers using
the parameter ``difficulty=simplest``

## Build instructions

    > CB_RESULT_DIR=npy CB_RANDOM_STATE=123 python create_bundle.py
    > zip bundle.zip -r --junk-paths npy/
    > sha1sum bundle.zip


