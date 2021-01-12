# UCR Time series repository

## Dataset information

* Number of datasets: 5
* Number of dimensions: 1
* Source: http://timeseriesclassification.com

## Build information

    > CB_DATASET_FILE=datasets.zip CB_RESULT_DIR=npy CB_INCLUDE_DATASET="Beef,Coffee,GunPoint,TwoLeadECG,SyntheticControl" python create_bundle.py
    > zip bundle.zip -r --junk-paths npy
    > sha1sum bundle.zip
