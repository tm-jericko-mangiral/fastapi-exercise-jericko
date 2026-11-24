import json
import os
import shutil
from pathlib import Path

DEFAULT_WORKING_DATA_DIR = ".runtime"
JSON_INDENT = 2


def prepare_working_copy(raw_path):
    """Copy a raw data file into the working directory.

    The copy replaces any earlier one, so every start begins from the raw
    data. The API reads and writes only the copy.

    :param raw_path: Location of the raw JSON file.
    :return: Path of the working copy.
    :raises ValueError: When the working copy would be the raw file itself.
    """
    raw_path = Path(raw_path)
    working_dir = Path(
        os.environ.get("WORKING_DATA_DIR", DEFAULT_WORKING_DATA_DIR)
    )
    working_path = working_dir / raw_path.name
    if working_path.resolve() == raw_path.resolve():
        raise ValueError(
            f"WORKING_DATA_DIR must differ from the folder of {raw_path}"
        )
    working_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(raw_path, working_path)
    return working_path


def write_json(path, data):
    """Write data to a JSON file, replacing its content.

    :param path: Location of the JSON file.
    :param data: JSON-serializable data.
    """
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=JSON_INDENT, ensure_ascii=False)
