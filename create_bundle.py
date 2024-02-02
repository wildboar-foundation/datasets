import io
import warnings
import requests
import zipfile
import os
import numpy as np
import pandas as pd
import sys
from wildboar.utils.variable_len import EoS, is_end_of_series


# The following code is adapted from the python package sktime to read .ts file.
# https://github.com/alan-turing-institute/sktime/blob/982ecd03a5c4ca73716e78a4161266a5960ebec4/sktime/utils/data_io.py#L12
class TsFileParseException(Exception):
    """
    Should be raised when parsing a .ts file and the format is incorrect.
    """

    pass


class LongFormatDataParseException(Exception):
    """
    Should be raised when parsing a .csv file
    with long-formatted date and the format is incorrect
    """

    pass


def load_from_tsfile_to_dataframe(
    io_dev,
    return_separate_X_and_y=True,
    replace_missing_vals_with="NaN",
):
    """Loads data from a .ts file into a Pandas DataFrame.
    Parameters
    ----------
    full_file_path_and_name: str
        The full pathname of the .ts file to read.
    return_separate_X_and_y: bool
        true if X and Y values should be returned as separate Data Frames (
        X) and a numpy array (y), false otherwise.
        This is only relevant for data that
    replace_missing_vals_with: str
       The value that missing values in the text file should be replaced
       with prior to parsing.
    Returns
    -------
    DataFrame, ndarray
        If return_separate_X_and_y then a tuple containing a DataFrame and a
        numpy array containing the relevant time-series and corresponding
        class values.
    DataFrame
        If not return_separate_X_and_y then a single DataFrame containing
        all time-series and (if relevant) a column "class_vals" the
        associated class values.
    """

    # Initialize flags and variables used when parsing the file

    metadata_started = False
    data_started = False

    has_problem_name_tag = False
    has_timestamps_tag = False
    has_univariate_tag = False
    has_class_labels_tag = False
    has_data_tag = False

    previous_timestamp_was_int = None
    prev_timestamp_was_timestamp = None
    num_dimensions = None
    is_first_case = True
    instance_list = []
    class_val_list = []
    line_num = 0

    # Parse the file
    # print(full_file_path_and_name)
    with io.TextIOWrapper(io_dev, encoding="utf-8", errors="ignore") as file:
        for line in file:
            # Strip white space from start/end of line and change to
            # lowercase for use below
            line = line.strip().lower()
            # Empty lines are valid at any point in a file
            if line:
                # Check if this line contains metadata
                # Please note that even though metadata is stored in this
                # function it is not currently published externally
                if line.startswith("@problemname"):
                    # Check that the data has not started
                    if data_started:
                        raise TsFileParseException("metadata must come before data")
                    # Check that the associated value is valid
                    tokens = line.split(" ")
                    token_len = len(tokens)

                    if token_len == 1:
                        raise TsFileParseException(
                            "problemname tag requires an associated value"
                        )

                    # problem_name = line[len("@problemname") + 1:]
                    has_problem_name_tag = True
                    metadata_started = True

                elif line.startswith("@timestamps"):
                    # Check that the data has not started

                    if data_started:
                        raise TsFileParseException("metadata must come before data")

                    # Check that the associated value is valid

                    tokens = line.split(" ")
                    token_len = len(tokens)

                    if token_len != 2:
                        raise TsFileParseException(
                            "timestamps tag requires an associated Boolean " "value"
                        )

                    elif tokens[1] == "true":
                        timestamps = True

                    elif tokens[1] == "false":
                        timestamps = False

                    else:
                        raise TsFileParseException("invalid timestamps value")

                    has_timestamps_tag = True
                    metadata_started = True

                elif line.startswith("@univariate"):
                    # Check that the data has not started

                    if data_started:
                        raise TsFileParseException("metadata must come before data")

                    # Check that the associated value is valid

                    tokens = line.split(" ")
                    token_len = len(tokens)

                    if token_len != 2:
                        raise TsFileParseException(
                            "univariate tag requires an associated Boolean  " "value"
                        )

                    elif tokens[1] == "true":
                        # univariate = True
                        pass

                    elif tokens[1] == "false":
                        # univariate = False
                        pass

                    else:
                        raise TsFileParseException("invalid univariate value")

                    has_univariate_tag = True
                    metadata_started = True

                elif line.startswith("@classlabel"):
                    # Check that the data has not started

                    if data_started:
                        raise TsFileParseException("metadata must come before data")

                    # Check that the associated value is valid

                    tokens = line.split(" ")
                    token_len = len(tokens)

                    if token_len == 1:
                        raise TsFileParseException(
                            "classlabel tag requires an associated Boolean  " "value"
                        )

                    if tokens[1] == "true":
                        class_labels = True

                    elif tokens[1] == "false":
                        class_labels = False

                    else:
                        raise TsFileParseException("invalid classLabel value")

                    # Check if we have any associated class values

                    if token_len == 2 and class_labels:
                        raise TsFileParseException(
                            "if the classlabel tag is true then class values "
                            "must be supplied"
                        )

                    has_class_labels_tag = True
                    class_label_list = [token.strip() for token in tokens[2:]]
                    metadata_started = True

                # Check if this line contains the start of data

                elif line.startswith("@data"):
                    if line != "@data":
                        raise TsFileParseException(
                            "data tag should not have an associated value"
                        )

                    if data_started and not metadata_started:
                        raise TsFileParseException("metadata must come before data")

                    else:
                        has_data_tag = True
                        data_started = True

                # If the 'data tag has been found then metadata has been
                # parsed and data can be loaded

                elif data_started:
                    # Check that a full set of metadata has been provided

                    if (
                        not has_problem_name_tag
                        or not has_timestamps_tag
                        or not has_univariate_tag
                        or not has_class_labels_tag
                        or not has_data_tag
                    ):
                        raise TsFileParseException(
                            "a full set of metadata has not been provided "
                            "before the data"
                        )

                    # Replace any missing values with the value specified

                    line = line.replace("?", replace_missing_vals_with)

                    # Check if we dealing with data that has timestamps

                    if timestamps:
                        # We're dealing with timestamps so cannot just split
                        # line on ':' as timestamps may contain one

                        has_another_value = False
                        has_another_dimension = False

                        timestamp_for_dim = []
                        values_for_dimension = []

                        this_line_num_dim = 0
                        line_len = len(line)
                        char_num = 0

                        while char_num < line_len:
                            # Move through any spaces

                            while char_num < line_len and str.isspace(line[char_num]):
                                char_num += 1

                            # See if there is any more data to read in or if
                            # we should validate that read thus far

                            if char_num < line_len:
                                # See if we have an empty dimension (i.e. no
                                # values)

                                if line[char_num] == ":":
                                    if len(instance_list) < (this_line_num_dim + 1):
                                        instance_list.append([])

                                    instance_list[this_line_num_dim].append(
                                        pd.Series(dtype="object")
                                    )
                                    this_line_num_dim += 1

                                    has_another_value = False
                                    has_another_dimension = True

                                    timestamp_for_dim = []
                                    values_for_dimension = []

                                    char_num += 1

                                else:
                                    # Check if we have reached a class label

                                    if line[char_num] != "(" and class_labels:
                                        class_val = line[char_num:].strip()

                                        if class_val not in class_label_list:
                                            raise TsFileParseException(
                                                "the class value '"
                                                + class_val
                                                + "' on line "
                                                + str(line_num + 1)
                                                + " is not "
                                                "valid"
                                            )

                                        class_val_list.append(class_val)
                                        char_num = line_len

                                        has_another_value = False
                                        has_another_dimension = False

                                        timestamp_for_dim = []
                                        values_for_dimension = []

                                    else:
                                        # Read in the data contained within
                                        # the next tuple

                                        if line[char_num] != "(" and not class_labels:
                                            raise TsFileParseException(
                                                "dimension "
                                                + str(this_line_num_dim + 1)
                                                + " on line "
                                                + str(line_num + 1)
                                                + " does "
                                                "not "
                                                "start "
                                                "with a "
                                                "'('"
                                            )

                                        char_num += 1
                                        tuple_data = ""

                                        while (
                                            char_num < line_len
                                            and line[char_num] != ")"
                                        ):
                                            tuple_data += line[char_num]
                                            char_num += 1

                                        if (
                                            char_num >= line_len
                                            or line[char_num] != ")"
                                        ):
                                            raise TsFileParseException(
                                                "dimension "
                                                + str(this_line_num_dim + 1)
                                                + " on line "
                                                + str(line_num + 1)
                                                + " does "
                                                "not end"
                                                " with a "
                                                "')'"
                                            )

                                        # Read in any spaces immediately
                                        # after the current tuple

                                        char_num += 1

                                        while char_num < line_len and str.isspace(
                                            line[char_num]
                                        ):
                                            char_num += 1

                                        # Check if there is another value or
                                        # dimension to process after this tuple

                                        if char_num >= line_len:
                                            has_another_value = False
                                            has_another_dimension = False

                                        elif line[char_num] == ",":
                                            has_another_value = True
                                            has_another_dimension = False

                                        elif line[char_num] == ":":
                                            has_another_value = False
                                            has_another_dimension = True

                                        char_num += 1

                                        # Get the numeric value for the
                                        # tuple by reading from the end of
                                        # the tuple data backwards to the
                                        # last comma

                                        last_comma_index = tuple_data.rfind(",")

                                        if last_comma_index == -1:
                                            raise TsFileParseException(
                                                "dimension "
                                                + str(this_line_num_dim + 1)
                                                + " on line "
                                                + str(line_num + 1)
                                                + " contains a tuple that has "
                                                "no comma inside of it"
                                            )

                                        try:
                                            value = tuple_data[last_comma_index + 1 :]
                                            value = float(value)

                                        except ValueError:
                                            raise TsFileParseException(
                                                "dimension "
                                                + str(this_line_num_dim + 1)
                                                + " on line "
                                                + str(line_num + 1)
                                                + " contains a tuple that does "
                                                "not have a valid numeric "
                                                "value"
                                            )

                                        # Check the type of timestamp that
                                        # we have

                                        timestamp = tuple_data[0:last_comma_index]

                                        try:
                                            timestamp = int(timestamp)
                                            timestamp_is_int = True
                                            timestamp_is_timestamp = False

                                        except ValueError:
                                            timestamp_is_int = False

                                        if not timestamp_is_int:
                                            try:
                                                timestamp = timestamp.strip()
                                                timestamp_is_timestamp = True

                                            except ValueError:
                                                timestamp_is_timestamp = False

                                        # Make sure that the timestamps in
                                        # the file (not just this dimension
                                        # or case) are consistent

                                        if (
                                            not timestamp_is_timestamp
                                            and not timestamp_is_int
                                        ):
                                            raise TsFileParseException(
                                                "dimension "
                                                + str(this_line_num_dim + 1)
                                                + " on line "
                                                + str(line_num + 1)
                                                + " contains a tuple that "
                                                "has an invalid timestamp '"
                                                + timestamp
                                                + "'"
                                            )

                                        if (
                                            previous_timestamp_was_int is not None
                                            and previous_timestamp_was_int
                                            and not timestamp_is_int
                                        ):
                                            raise TsFileParseException(
                                                "dimension "
                                                + str(this_line_num_dim + 1)
                                                + " on line "
                                                + str(line_num + 1)
                                                + " contains tuples where the "
                                                "timestamp format is "
                                                "inconsistent"
                                            )

                                        if (
                                            prev_timestamp_was_timestamp is not None
                                            and prev_timestamp_was_timestamp
                                            and not timestamp_is_timestamp
                                        ):
                                            raise TsFileParseException(
                                                "dimension "
                                                + str(this_line_num_dim + 1)
                                                + " on line "
                                                + str(line_num + 1)
                                                + " contains tuples where the "
                                                "timestamp format is "
                                                "inconsistent"
                                            )

                                        # Store the values

                                        timestamp_for_dim += [timestamp]
                                        values_for_dimension += [value]

                                        #  If this was our first tuple then
                                        #  we store the type of timestamp we
                                        #  had

                                        if (
                                            prev_timestamp_was_timestamp is None
                                            and timestamp_is_timestamp
                                        ):
                                            prev_timestamp_was_timestamp = True
                                            previous_timestamp_was_int = False

                                        if (
                                            previous_timestamp_was_int is None
                                            and timestamp_is_int
                                        ):
                                            prev_timestamp_was_timestamp = False
                                            previous_timestamp_was_int = True

                                        # See if we should add the data for
                                        # this dimension

                                        if not has_another_value:
                                            if len(instance_list) < (
                                                this_line_num_dim + 1
                                            ):
                                                instance_list.append([])

                                            if timestamp_is_timestamp:
                                                timestamp_for_dim = pd.DatetimeIndex(
                                                    timestamp_for_dim
                                                )

                                            instance_list[this_line_num_dim].append(
                                                pd.Series(
                                                    index=timestamp_for_dim,
                                                    data=values_for_dimension,
                                                )
                                            )
                                            this_line_num_dim += 1

                                            timestamp_for_dim = []
                                            values_for_dimension = []

                            elif has_another_value:
                                raise TsFileParseException(
                                    "dimension " + str(this_line_num_dim + 1) + " on "
                                    "line "
                                    + str(line_num + 1)
                                    + " ends with a ',' that "
                                    "is not followed by "
                                    "another tuple"
                                )

                            elif has_another_dimension and class_labels:
                                raise TsFileParseException(
                                    "dimension " + str(this_line_num_dim + 1) + " on "
                                    "line "
                                    + str(line_num + 1)
                                    + " ends with a ':' while "
                                    "it should list a class "
                                    "value"
                                )

                            elif has_another_dimension and not class_labels:
                                if len(instance_list) < (this_line_num_dim + 1):
                                    instance_list.append([])

                                instance_list[this_line_num_dim].append(
                                    pd.Series(dtype=np.float32)
                                )
                                this_line_num_dim += 1
                                num_dimensions = this_line_num_dim

                            # If this is the 1st line of data we have seen
                            # then note the dimensions

                            if not has_another_value and not has_another_dimension:
                                if num_dimensions is None:
                                    num_dimensions = this_line_num_dim

                                if num_dimensions != this_line_num_dim:
                                    raise TsFileParseException(
                                        "line "
                                        + str(line_num + 1)
                                        + " does not have the "
                                        "same number of "
                                        "dimensions as the "
                                        "previous line of "
                                        "data"
                                    )

                        # Check that we are not expecting some more data,
                        # and if not, store that processed above

                        if has_another_value:
                            raise TsFileParseException(
                                "dimension "
                                + str(this_line_num_dim + 1)
                                + " on line "
                                + str(line_num + 1)
                                + " ends with a ',' that is "
                                "not followed by another "
                                "tuple"
                            )

                        elif has_another_dimension and class_labels:
                            raise TsFileParseException(
                                "dimension "
                                + str(this_line_num_dim + 1)
                                + " on line "
                                + str(line_num + 1)
                                + " ends with a ':' while it "
                                "should list a class value"
                            )

                        elif has_another_dimension and not class_labels:
                            if len(instance_list) < (this_line_num_dim + 1):
                                instance_list.append([])

                            instance_list[this_line_num_dim].append(
                                pd.Series(dtype="object")
                            )
                            this_line_num_dim += 1
                            num_dimensions = this_line_num_dim

                        # If this is the 1st line of data we have seen then
                        # note the dimensions

                        if (
                            not has_another_value
                            and num_dimensions != this_line_num_dim
                        ):
                            raise TsFileParseException(
                                "line " + str(line_num + 1) + " does not have the same "
                                "number of dimensions as the "
                                "previous line of data"
                            )

                        # Check if we should have class values, and if so
                        # that they are contained in those listed in the
                        # metadata

                        if class_labels and len(class_val_list) == 0:
                            raise TsFileParseException(
                                "the cases have no associated class values"
                            )

                    else:
                        dimensions = line.split(":")

                        # If first row then note the number of dimensions (
                        # that must be the same for all cases)

                        if is_first_case:
                            num_dimensions = len(dimensions)

                            if class_labels:
                                num_dimensions -= 1

                            for _dim in range(0, num_dimensions):
                                instance_list.append([])

                            is_first_case = False

                        # See how many dimensions that the case whose data
                        # in represented in this line has

                        this_line_num_dim = len(dimensions)

                        if class_labels:
                            this_line_num_dim -= 1

                        # All dimensions should be included for all series,
                        # even if they are empty

                        if this_line_num_dim != num_dimensions:
                            raise TsFileParseException(
                                "inconsistent number of dimensions. "
                                "Expecting "
                                + str(num_dimensions)
                                + " but have read "
                                + str(this_line_num_dim)
                            )

                        # Process the data for each dimension

                        for dim in range(0, num_dimensions):
                            dimension = dimensions[dim].strip()

                            if dimension:
                                data_series = dimension.split(",")
                                data_series = [float(i) for i in data_series]
                                instance_list[dim].append(pd.Series(data_series))

                            else:
                                instance_list[dim].append(pd.Series(dtype="object"))

                        if class_labels:
                            class_val_list.append(dimensions[num_dimensions].strip())

            line_num += 1

    # Check that the file was not empty

    if line_num:
        # Check that the file contained both metadata and data

        if metadata_started and not (
            has_problem_name_tag
            and has_timestamps_tag
            and has_univariate_tag
            and has_class_labels_tag
            and has_data_tag
        ):
            raise TsFileParseException("metadata incomplete")

        elif metadata_started and not data_started:
            raise TsFileParseException("file contained metadata but no data")

        elif metadata_started and data_started and len(instance_list) == 0:
            raise TsFileParseException("file contained metadata but no data")

        # Create a DataFrame from the data parsed above

        data = pd.DataFrame(dtype=np.float32)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for dim in range(0, num_dimensions):
                data["dim_" + str(dim)] = instance_list[dim]

        data = data.copy()

        # Check if we should return any associated class labels separately

        if class_labels:
            if return_separate_X_and_y:
                return data, np.asarray(class_val_list)

            else:
                data["class_vals"] = pd.Series(class_val_list)
                return data
        else:
            return data

    else:
        raise TsFileParseException("empty file")


def download_file(url, filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total_length = r.headers.get("content-length")
        length = 0
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                length += len(chunk)
                sys.stdout.write(f"{length}/{total_length}")
                f.write(chunk)
                sys.stdout.flush()
                sys.stdout.write("\r")
    return filename


if __name__ == "__main__":
    DATASET_FILE = os.environ.get("CB_DATASET_FILE", "datasets.zip")
    RESULT_DIR = os.environ.get("CB_RESULT_DIR", "npz")
    if not os.path.exists(DATASET_FILE):
        download_file(
            "http://www.timeseriesclassification.com/aeon-toolkit/Archives/Multivariate2018_ts.zip",
            DATASET_FILE,
        )
    if not os.path.exists(RESULT_DIR):
        os.mkdir(RESULT_DIR)

    with zipfile.ZipFile(DATASET_FILE) as archive:
        for archive_file in archive.filelist:
            path, ext = os.path.splitext(archive_file.filename)
            filename = os.path.basename(path)
            if ext == ".ts" and (
                filename.endswith("_TRAIN") or filename.endswith("_TEST")
            ):
                df_x, y = load_from_tsfile_to_dataframe(archive.open(archive_file))
                n_timestep = max(
                    max(df_x[col].loc[i].size for i in range(len(df_x[col])))
                    for col in df_x
                )
                n_samples, n_dims = df_x.shape
                labels, index, inv = np.unique(
                    y, return_index=True, return_inverse=True
                )
                print(
                    "%s: %r"
                    % (
                        filename,
                        list("%s -> %r" % (l, inv[i]) for l, i in zip(labels, index)),
                    ),
                )

                # We use -INF to represent end of sequence
                x = np.full((n_samples, n_dims, n_timestep), EoS, dtype=np.float32)

                for dim, col in enumerate(df_x):
                    df_dim = df_x[col]
                    for sample, sample_col in enumerate(df_dim):
                        x[sample, dim, : len(sample_col)] = sample_col.values

                x = np.squeeze(x)
                assert (
                    is_end_of_series(x.astype(np.float64)).sum()
                    == is_end_of_series(x).sum()
                )
                np.savez(
                    os.path.join(RESULT_DIR, filename) + ".npz",
                    x=x,
                    y=inv.reshape(-1),
                    labels=y,
                )
