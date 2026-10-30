"""Where the engine finds its data: the folder named by `PANTHER_DATA_DIR`.

Each service's data is under `<service>/<version>/`. cSNP's frozen PANTHER 9 data is under
`csnp/9/`, whether the folder holds the sample or the full library.
"""

import os
from pathlib import Path

DATA_DIR_VARIABLE = "PANTHER_DATA_DIR"


class DataFolderError(Exception):
    """No data folder was given, and `PANTHER_DATA_DIR` isn't set."""


def data_root(folder: Path | str | None = None) -> Path:
    """`folder` if given, otherwise the folder `PANTHER_DATA_DIR` names."""
    if folder is not None:
        return Path(folder)
    value = os.environ.get(DATA_DIR_VARIABLE, "")
    if not value:
        raise DataFolderError(
            f"{DATA_DIR_VARIABLE} isn't set: set it to the data folder, or pass --data-dir"
        )
    return Path(value)


def service_folder(service: str, version: str, folder: Path | str | None = None) -> Path:
    """A service's data folder for one data version, such as `<root>/csnp/9`."""
    return data_root(folder) / service / version
