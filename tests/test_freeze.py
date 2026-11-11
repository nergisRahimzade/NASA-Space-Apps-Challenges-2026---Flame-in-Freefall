"""Day 17 (FIF-D17-DAT): master.csv v1 is frozen.

data/freeze.json records a fingerprint, row count and columns for every file the data pipeline
writes, and a fingerprint for every raw table it reads. These tests fail if any of them change
without a new version being recorded (data_notes.md section 14). test_master.py and
test_ranking.py already check that a fresh build from data/raw/ matches the saved files, so
together: raw tables -> fresh build == saved files == frozen record.
"""

import json
import shutil

import pandas as pd
import pytest

from flame_in_freefall.freeze_data import (
    FREEZE,
    INPUTS,
    OUTPUTS,
    ROOT,
    differences,
    fingerprint,
    load_record,
    make_record,
)


@pytest.fixture(scope="module")
def record():
    return load_record()


def test_saved_files_match_the_freeze(record):
    assert differences(record) == []


def test_master_v1_is_the_419_row_table(record):
    assert record["version"] == "1.0"
    assert record["git_tag"] == "data-v1.0"
    assert record["rows_per_experiment"] == {
        "FLEX-2": 8,
        "Saffire-II": 9,
        "FLEX": 273,
        "BASS-II": 129,
    }
    master = record["outputs"]["data/master.csv"]
    assert master["rows"] == 419
    assert master["columns"] == list(pd.read_csv(ROOT / "data" / "master.csv").columns)


def test_record_covers_every_input_and_output(record):
    assert set(record["inputs"]) == {p.relative_to(ROOT).as_posix() for p in INPUTS}
    assert set(record["outputs"]) == {p.relative_to(ROOT).as_posix() for p in OUTPUTS}


def test_record_is_what_make_record_writes(record):
    # Catches a hand-edited freeze.json: only the date can differ from a fresh record.
    fresh = make_record(record["version"], record["frozen_on"])
    assert json.loads(FREEZE.read_text(encoding="utf-8")) == fresh


def test_fingerprint_ignores_windows_line_endings(tmp_path):
    unix, windows = tmp_path / "unix.csv", tmp_path / "windows.csv"
    unix.write_bytes(b"a,b\n1,2\n")
    windows.write_bytes(b"a,b\r\n1,2\r\n")
    assert fingerprint(unix) == fingerprint(windows)


# A copy of the repo's data files, so the tests below can change them safely.
@pytest.fixture
def copy_root(tmp_path):
    for path in [*INPUTS, *OUTPUTS]:
        target = tmp_path / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, target)
    return tmp_path


def test_a_changed_value_is_reported(record, copy_root):
    master = copy_root / "data" / "master.csv"
    table = pd.read_csv(master)
    table.loc[0, "oxygen_pct_min"] += 1
    table.to_csv(master, index=False)
    assert differences(record, copy_root) == [
        "data/master.csv: changed since the v1.0 freeze (values changed)"
    ]


def test_new_rows_and_columns_are_named(record, copy_root):
    master = copy_root / "data" / "master.csv"
    table = pd.read_csv(master)
    table = pd.concat([table, table.tail(1)]).assign(extra=1)
    table.to_csv(master, index=False)
    assert differences(record, copy_root) == [
        "data/master.csv: changed since the v1.0 freeze (419 -> 420 rows; new columns ['extra'])"
    ]


def test_changed_raw_table_and_missing_file_are_reported(record, copy_root):
    raw = INPUTS[0].relative_to(ROOT).as_posix()
    (copy_root / raw).write_text("edited\n", encoding="utf-8")
    (copy_root / "data" / "ranking.csv").unlink()
    assert differences(record, copy_root) == [
        f"{raw}: raw input changed since the v1.0 freeze",
        "data/ranking.csv: missing (frozen in v1.0)",
    ]
