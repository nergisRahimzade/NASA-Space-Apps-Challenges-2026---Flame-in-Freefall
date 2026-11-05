"""FIF-D10-DAT: data quality tests (range checks and duplicate checks).

The first half checks that the real data passes. The second half plants one mistake and
checks that it is caught, so a check that silently stopped working would fail here too."""

import pandas as pd
import pytest

from flame_in_freefall.build_master import build_master
from flame_in_freefall.check_data import (
    ID_COLUMNS,
    KNOWN_SAME_TIME,
    duplicate_problems,
    flex_consistency_problems,
    range_problems,
    same_time_tests,
)
from flame_in_freefall.clean_tables import clean_flex, clean_flex2, clean_saffire2


@pytest.fixture(scope="module")
def tables() -> dict[str, pd.DataFrame]:
    # Built from the raw files, like tests/test_master.py, so data/clean/ can't be stale.
    return {"flex2.csv": clean_flex2(), "saffire2.csv": clean_saffire2(), "flex.csv": clean_flex()}


@pytest.fixture(scope="module")
def master(tables) -> pd.DataFrame:
    return build_master(list(tables.values()))


def with_value(table: pd.DataFrame, col: str, value, row: int = 0) -> pd.DataFrame:
    """A copy of the table with one cell changed."""
    changed = table.copy()
    changed.loc[row, col] = value
    return changed


# --- The real data passes ------------------------------------------------------------


@pytest.mark.parametrize("name", ID_COLUMNS)
def test_clean_table_values_in_range(tables, name):
    assert range_problems(tables[name]) == []


def test_master_values_in_range(master):
    assert range_problems(master) == []


@pytest.mark.parametrize("name", ID_COLUMNS)
def test_each_fuel_sample_or_test_listed_once(tables, name):
    assert duplicate_problems(tables[name], ID_COLUMNS[name]) == []


def test_flex_gas_mix_and_droplet_sizes_make_sense(tables):
    assert flex_consistency_problems(tables["flex.csv"]) == []


def test_only_known_flex_tests_share_a_date_and_time():
    # A new clash means a new copy-paste mistake (or a new repeated test) in the raw file.
    assert same_time_tests() == KNOWN_SAME_TIME


# --- The checks catch planted mistakes -----------------------------------------------


@pytest.mark.parametrize(
    "col, value",
    [
        ("oxygen_pct_min", 0.21),  # mole fraction, not x100
        ("pressure_kpa_max", 760.0),  # mmHg, not turned into kPa
        ("pressure_kpa_min", 1.0),  # atm, not turned into kPa
        ("flow_cm_s_max", 200.0),  # mm/s instead of cm/s
        ("oxygen_pct_min", 40.0),  # in range, but above oxygen_pct_max (30)
        ("experiment", "BASS"),  # out of scope
        ("outcome", "Extinguished"),  # not one of the 3 FLEX outcomes
    ],
)
def test_range_check_catches_a_bad_value(master, col, value):
    assert len(range_problems(with_value(master, col, value))) == 1


def test_range_check_catches_a_date_outside_flex(tables):
    assert len(range_problems(with_value(tables["flex.csv"], "test_date", "2090-01-01"))) == 1


def test_duplicate_check_catches_a_repeated_test(tables):
    flex = tables["flex.csv"]
    doubled = pd.concat([flex, flex.iloc[[5]]], ignore_index=True)
    repeated = flex.at[5, "test_id"]
    assert duplicate_problems(doubled, "test_id") == [f"FLEX {repeated}: listed 2 times"]


def test_flex_consistency_catches_bad_rows(tables):
    flex = tables["flex.csv"]
    row = flex["droplet_diameter_mm"].first_valid_index()
    too_much_gas = with_value(flex, "helium_pct", 50.0, row)
    grown_flame = with_value(
        flex, "extinction_diameter_mm", flex.at[row, "droplet_diameter_mm"] + 1, row
    )
    assert len(flex_consistency_problems(too_much_gas)) == 1
    assert len(flex_consistency_problems(grown_flame)) == 1
