"""Day 9 (BE): get_table() reads data/master.csv, filters it and rejects bad filters.

Uses the real master.csv (419 rows, built by the data role); counts come from data_notes.md."""

import pytest

from flame_in_freefall.api import get_table

COLUMNS = {
    "experiment",
    "material",
    "material_category",
    "oxygen_pct_min",
    "oxygen_pct_max",
    "pressure_kpa_min",
    "pressure_kpa_max",
    "flow_cm_s_min",
    "flow_cm_s_max",
    "suppressant",
    "suppressant_pct",
    "spread_rate_mm_s",
    "spread_rate_per_flow",
    "outcome",
}


def test_all_rows_have_the_contract_columns():
    rows = get_table()
    assert len(rows) == 419
    assert all(set(r) == COLUMNS for r in rows)


def test_no_filters_and_none_are_the_same():
    assert get_table(None) == get_table({}) == get_table()


def test_empty_cells_are_none():
    saffire = get_table({"experiment": "Saffire-II"})
    assert len(saffire) == 9
    assert all(r["pressure_kpa_min"] is None for r in saffire)  # Saffire-II has no pressure


def test_material_and_category_filters():
    assert {r["material"] for r in get_table({"material": "Heptane"})} == {"Heptane"}
    fabric = get_table({"material_category": "fabric"})
    assert fabric and all(r["material_category"] == "fabric" for r in fabric)


def test_filters_combine():
    rows = get_table({"experiment": "FLEX", "material": "Heptane"})
    assert rows and all(r["experiment"] == "FLEX" and r["material"] == "Heptane" for r in rows)


def test_oxygen_range_that_overlaps_the_filter_matches():
    # FLEX-2 rows cover 17-30 % oxygen, so they match a 20-25 % filter.
    assert len(get_table({"experiment": "FLEX-2", "oxygen_min": 20, "oxygen_max": 25})) == 8


def test_oxygen_outside_the_filter_does_not_match():
    rows = get_table({"oxygen_min": 20, "oxygen_max": 25})
    assert rows and all(r["oxygen_pct_max"] >= 20 and r["oxygen_pct_min"] <= 25 for r in rows)
    assert not get_table({"experiment": "FLEX", "oxygen_min": 35})  # FLEX tops out at 34 %


def test_unknown_value_gives_no_rows():
    assert get_table({"experiment": "BASS"}) == []  # not found, never invented


@pytest.mark.parametrize(
    "bad",
    [
        {"colour": "red"},  # typo in a key
        {"material": "  "},  # blank text
        {"experiment": 5},  # text filter given a number
        {"oxygen_min": "20"},  # number filter given text
        {"oxygen_max": True},  # bool is not a number here
        {"oxygen_min": 30, "oxygen_max": 20},  # min above max
    ],
)
def test_bad_filters_are_rejected(bad):
    with pytest.raises(ValueError):
        get_table(bad)
