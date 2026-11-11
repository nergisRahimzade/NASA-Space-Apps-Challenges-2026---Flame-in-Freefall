"""Day 15 (DAT): the glossary file follows its rules and covers what the app shows."""

import json

import pandas as pd
import pytest

from flame_in_freefall.glossary import GLOSSARY, column_help, load_glossary

ROOT = GLOSSARY.parents[1]
TERMS = load_glossary()  # also checks the saved file follows the rules
BY_ID = {t["id"]: t for t in TERMS}


def test_ticket_terms_are_there():
    # FIF-D15-DAT asks for plain-word definitions of LOI and spread rate.
    assert "Limiting Oxygen Index" in BY_ID["loi"]["term"]
    assert "mm/s" in BY_ID["spread_rate"]["tooltip"]


def test_every_master_column_has_a_tooltip():
    # Each table header in the app gets a tooltip, so no column is left unexplained.
    master = pd.read_csv(ROOT / "data" / "master.csv", nrows=0)
    assert set(master.columns) <= set(column_help(TERMS))


def test_tooltip_columns_exist_in_the_data():
    # A typo in a column name would silently never show its tooltip.
    known = set(pd.read_csv(ROOT / "data" / "master.csv", nrows=0).columns)
    known |= set(pd.read_csv(ROOT / "data" / "ranking.csv", nrows=0).columns)
    assert set(column_help(TERMS)) <= known


def test_experiment_names_in_tooltips_match_the_data():
    # The experiment tooltip names every experiment the table has.
    experiments = pd.read_csv(ROOT / "data" / "master.csv")["experiment"].unique()
    for name in experiments:
        assert name in BY_ID["experiment"]["tooltip"], name


def _write(tmp_path, terms) -> str:
    path = tmp_path / "glossary.json"
    path.write_text(json.dumps({"terms": terms}), encoding="utf-8")
    return path


GOOD = {"id": "loi", "term": "LOI", "tooltip": "Lowest oxygen to keep burning.", "columns": []}


@pytest.mark.parametrize(
    ("terms", "message"),
    [
        ([{**GOOD, "tooltip": " "}], "non-empty tooltip"),
        ([{k: v for k, v in GOOD.items() if k != "columns"}], "exactly the fields"),
        ([{**GOOD, "tooltip": "x" * 251}], "over 250"),
        ([GOOD, GOOD], "listed twice"),
        (
            [{**GOOD, "columns": ["a"]}, {**GOOD, "id": "other", "columns": ["a"]}],
            "already have a tooltip",
        ),
    ],
)
def test_broken_glossary_fails_loudly(tmp_path, terms, message):
    with pytest.raises(ValueError, match=message):
        load_glossary(_write(tmp_path, terms))


def test_column_help_maps_each_column():
    terms = [{**GOOD, "columns": ["oxygen_pct_min", "oxygen_pct_max"]}]
    assert column_help(terms) == {
        "oxygen_pct_min": GOOD["tooltip"],
        "oxygen_pct_max": GOOD["tooltip"],
    }
