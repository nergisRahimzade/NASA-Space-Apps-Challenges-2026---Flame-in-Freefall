"""Day 18 (FIF-D18-DAT): data_card.md stays in step with the frozen data.

The card is written by hand, so these checks fail CI if the data changes (a new freeze version,
new rows, a new source) and the card isn't updated with it."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = (ROOT / "data_card.md").read_text(encoding="utf-8")
FREEZE = json.loads((ROOT / "data" / "freeze.json").read_text(encoding="utf-8"))


def _downloads() -> list[dict]:
    with open(ROOT / "data" / "downloads.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_card_names_the_frozen_version_and_tag():
    assert f"data v{FREEZE['version']}" in CARD
    assert f"frozen {FREEZE['frozen_on']}" in CARD
    assert FREEZE["git_tag"] in CARD


def test_card_row_counts_match_the_freeze():
    master = FREEZE["outputs"]["data/master.csv"]
    assert f"{master['rows']} rows, {len(master['columns'])} columns" in CARD
    assert f"**{master['rows']}**" in CARD  # the total in the sources table
    for experiment, rows in FREEZE["rows_per_experiment"].items():
        # The experiment's row in the sources table ends with its row count
        line = next(row for row in CARD.splitlines() if row.startswith(f"| {experiment} |"))
        assert line.rstrip(" |").endswith(f"| {rows}"), line


def test_card_lists_every_master_column():
    for column in FREEZE["outputs"]["data/master.csv"]["columns"]:
        assert f"`{column}`" in CARD, column


def test_card_lists_every_raw_file_with_its_link_and_date():
    for row in _downloads():
        assert row["file_name"] in CARD, row["file_name"]
        assert row["source_url"] in CARD, row["source_url"]
        assert row["download_date"] in CARD, row["download_date"]


def test_card_commands_point_at_real_modules():
    modules = set(re.findall(r"python -m flame_in_freefall\.(\w+)", CARD))
    assert {"freeze_data", "clean_tables", "ingest"} <= modules
    for name in modules:
        assert (ROOT / "src" / "flame_in_freefall" / f"{name}.py").exists(), name


def test_card_never_claims_nasa_endorsement():
    assert "according to NASA" not in CARD
    assert "has not reviewed or endorsed" in CARD
