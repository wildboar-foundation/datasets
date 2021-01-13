import os
import numpy as np
from wildboar.datasets import load_datasets
from wildboar.datasets.outlier import EmmottLabeler

if __name__ == "__main__":
    RESULT_DIR = os.environ.get("CB_RESULT_DIR", "npy")
    RANDOM_STATE = int(os.environ.get("CB_RANDOM_STATE", "123"))

    if not os.path.exists(RESULT_DIR):
        os.mkdir(RESULT_DIR)

    for dataset, (x, y) in load_datasets("wildboar/ucr"):
        print(dataset, x)
        labeler = EmmottLabeler(
            n_outliers=0.05, difficulty="simplest", random_state=RANDOM_STATE
        )
        new_x, new_y = labeler.fit_transform(x, y)
        np.save(
            os.path.join(RESULT_DIR, dataset + ".npy"),
            np.concatenate([new_x, new_y.reshape(-1, 1)], axis=1),
        )
