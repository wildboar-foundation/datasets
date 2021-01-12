import io
import requests
import zipfile
import os
import numpy as np
from scipy.io.arff import loadarff


def download_file(url, filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return filename


if __name__ == "__main__":
    DATASET_FILE = os.environ.get("CB_DATASET_FILE", "datasets.zip")
    RESULT_DIR = os.environ.get("CB_RESULT_DIR", "npy")
    if not os.path.exists(DATASET_FILE):
        download_file(
            "http://www.timeseriesclassification.com/Downloads/Archives/Univariate2018_arff.zip",
            DATASET_FILE,
        )
    if not os.path.exists(RESULT_DIR):
        os.mkdir(RESULT_DIR)

    with zipfile.ZipFile(DATASET_FILE) as archive:
        for archive_file in archive.filelist:
            path, ext = os.path.splitext(archive_file.filename)
            filename = os.path.basename(path)
            if ext == ".arff" and (
                filename.endswith("_TRAIN") or filename.endswith("_TEST")
            ):
                with io.TextIOWrapper(
                    archive.open(archive_file), encoding="utf-8"
                ) as io_wrapper:
                    arff, _metadata = loadarff(io_wrapper)
                    arr = np.array(arff.tolist())
                    np.save(
                        os.path.join(RESULT_DIR, filename) + ".npy",
                        arr,
                        allow_pickle=False,
                        fix_imports=False,
                    )
