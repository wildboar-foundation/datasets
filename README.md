# Time series outlier detection

## Dataset information

- Number of datasets: 128
- Number of dimensions: 1
- Source: http://timeseriesclassification.com

These datasets are constructed using the `EmmottLabler` with ~5% outliers using
the parameter ``difficulty=simplest``

## Build instructions

    > CB_RESULT_DIR=npy-simplest CB_RANDOM_STATE=123 CB_DIFFICULTY=simplest python create_bundle.py
    > zip easy.zip -r --junk-paths npy-simplest/
    > sha1sum easy.zip | cut -d " " -f 1 > easy.sha1
    > CB_RESULT_DIR=npy-hardest CB_RANDOM_STATE=123 CB_DIFFICULTY=hardest python create_bundle.py
    > zip hard.zip -r --junk-paths npy-hardest/
    > sha1sum hard.zip | cut -d " " -f 1 > hard.sha1


