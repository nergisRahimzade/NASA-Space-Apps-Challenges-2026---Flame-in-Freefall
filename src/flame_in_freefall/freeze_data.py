"""Day 17 (FIF-D17-DAT): freeze master.csv v1.

One command re-runs the whole data pipeline from data/raw/, in order:
clean_tables -> build_master -> build_ranking -> check_data. Then it compares the files with
data/freeze.json, the record of the frozen version (a fingerprint, row count and columns for
each file). Rules and reasons: data_notes.md section 14.

Run from the repo root:
    uv run python -m flame_in_freefall.freeze_data
        re-run everything and check nothing changed since the freeze (exit 1 if it did)
    uv run python -m flame_in_freefall.freeze_data --write --version 1.1
        record a new version, only after the team agrees to change the frozen data

tests/test_freeze.py checks the saved files against data/freeze.json in CI.
"""

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from flame_in_freefall import build_master, build_ranking, check_data, clean_tables
from flame_in_freefall.build_master import CLEAN, CLEAN_FILES, MASTER
from flame_in_freefall.build_ranking import RANKING

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "data" / "freeze.json"

# The raw tables the pipeline reads. If one changes, the frozen files may no longer follow.
INPUTS = [
    clean_tables.FLEX2_RAW,
    clean_tables.SAFFIRE2_RAW,
    clean_tables.FLEX_RAW,
    clean_tables.BASS2_RAW,
]
# The files the pipeline writes. master.csv is the one other code reads (get_table()).
OUTPUTS = [MASTER, RANKING, *(CLEAN / name for name in CLEAN_FILES)]


def fingerprint(path: Path) -> str:
    """SHA-256 of the file, with Windows line endings read as Unix ones.

    pandas writes CRLF on Windows and Git stores LF, so the same table would otherwise get two
    fingerprints depending on who built it.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def describe(path: Path) -> dict:
    """Fingerprint, row count and column names of one CSV."""
    table = pd.read_csv(path)
    return {"sha256": fingerprint(path), "rows": len(table), "columns": list(table.columns)}


def make_record(version: str, frozen_on: str, root: Path = ROOT) -> dict:
    master = pd.read_csv(root / _rel(MASTER, ROOT))
    return {
        "version": version,
        "frozen_on": frozen_on,
        "git_tag": f"data-v{version}",
        "rows_per_experiment": master["experiment"].value_counts(sort=False).to_dict(),
        "outputs": {_rel(p, ROOT): describe(root / _rel(p, ROOT)) for p in OUTPUTS},
        "inputs": {_rel(p, ROOT): fingerprint(root / _rel(p, ROOT)) for p in INPUTS},
    }


def differences(record: dict, root: Path = ROOT) -> list[str]:
    """Every way the files under root differ from the freeze record. Empty = still frozen."""
    version = record["version"]
    problems = []
    for name, expected in record["inputs"].items():
        path = root / name
        if not path.exists():
            problems.append(f"{name}: missing (raw input of v{version})")
        elif fingerprint(path) != expected:
            problems.append(f"{name}: raw input changed since the v{version} freeze")
    for name, expected in record["outputs"].items():
        path = root / name
        if not path.exists():
            problems.append(f"{name}: missing (frozen in v{version})")
            continue
        actual = describe(path)
        if actual["sha256"] == expected["sha256"]:
            continue
        detail = []
        if actual["rows"] != expected["rows"]:
            detail.append(f"{expected['rows']} -> {actual['rows']} rows")
        added = [c for c in actual["columns"] if c not in expected["columns"]]
        dropped = [c for c in expected["columns"] if c not in actual["columns"]]
        if added:
            detail.append(f"new columns {added}")
        if dropped:
            detail.append(f"columns gone {dropped}")
        why = f" ({'; '.join(detail)})" if detail else " (values changed)"
        problems.append(f"{name}: changed since the v{version} freeze{why}")
    return problems


def load_record(path: Path = FREEZE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rebuild() -> None:
    """Re-run the pipeline from data/raw/. Stops (exit 1) if check_data finds a problem."""
    clean_tables.main()
    build_master.main()
    build_ranking.main()
    check_data.main()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Re-run the data pipeline and check the freeze.")
    parser.add_argument("--write", action="store_true", help="record a new frozen version")
    parser.add_argument("--version", help='version to record with --write, e.g. "1.1"')
    args = parser.parse_args(argv)
    if args.write and not args.version:
        parser.error("--write needs --version")

    rebuild()
    print()

    if args.write:
        if FREEZE.exists() and load_record()["version"] == args.version:
            if differences(load_record()):
                sys.exit(f"v{args.version} is already frozen with other data. Use a new version.")
        record = make_record(args.version, datetime.date.today().isoformat())
        FREEZE.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"Recorded v{args.version} in data/freeze.json. Tag it: {record['git_tag']}")
        return

    record = load_record()
    problems = differences(record)
    if not problems:
        rows = record["outputs"]["data/master.csv"]["rows"]
        print(f"master.csv v{record['version']} ({rows} rows): re-run matches the freeze.")
        return
    print(f"{len(problems)} difference(s) from the v{record['version']} freeze:")
    print("\n".join(f"- {p}" for p in problems))
    print("If the change is wanted, the team agrees on it, then: --write --version <new>")
    sys.exit(1)


if __name__ == "__main__":
    main()
