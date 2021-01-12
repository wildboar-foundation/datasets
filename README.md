# UCR Time series repository

## Dataset information

- Number of datasets: 128
- Number of dimensions: 1
- Source: http://timeseriesclassification.com

## Build instructions

    > CB_DATASET_FILE=dataset.zip CB_RESULT_DIR=npy python create_bundle.zip
    > zip bundle.zip -r --junk-paths npy/
    > sha1sum bundle.zip


