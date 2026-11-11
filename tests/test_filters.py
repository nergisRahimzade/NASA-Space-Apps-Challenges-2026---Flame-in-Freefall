"""Day 17 (FE): the single filter state shared by search, the table and every chart."""

import pandas as pd

from flame_in_freefall.filters import (
    ALL,
    Filters,
    from_choices,
    material_options,
    material_oxygen_test_counts,
)

ROWS = pd.DataFrame(
    {
        "experiment": ["FLEX", "FLEX", "FLEX", "Saffire-II", "FLEX-2"],
        "material": ["Heptane", "Heptane", "Methanol", "PMMA", "Decane"],
        "oxygen_pct_min": [21.0, 21.0, 18.0, 21.5, 17.0],
        "oxygen_pct_max": [21.0, 21.0, 18.0, 22.1, 30.0],
    }
)


def test_all_means_no_filter():
    f = from_choices(ALL, ALL, (12, 34))
    assert f == Filters(experiment=None, material=None, oxygen_min=12.0, oxygen_max=34.0)
    assert f.table_filters() == {"oxygen_min": 12.0, "oxygen_max": 34.0}


def test_table_filters_match_the_contract_keys():
    f = from_choices("FLEX", "Heptane", (15, 30))
    assert f.table_filters() == {
        "experiment": "FLEX",
        "material": "Heptane",
        "oxygen_min": 15.0,
        "oxygen_max": 30.0,
    }


def test_describe_reads_as_one_line():
    assert from_choices(ALL, ALL, (12, 34)).describe() == (
        "All experiments · all materials · 12–34% oxygen"
    )
    assert from_choices("FLEX", "Heptane", (15.5, 30)).describe() == (
        "FLEX · Heptane · 15.5–30% oxygen"
    )


def test_material_options_follow_the_experiment():
    assert material_options(ROWS, ALL) == [ALL, "Decane", "Heptane", "Methanol", "PMMA"]
    assert material_options(ROWS, "FLEX") == [ALL, "Heptane", "Methanol"]


def test_test_counts_by_material_and_oxygen_leave_out_flex2():
    grid = material_oxygen_test_counts(ROWS)
    assert list(grid.index) == ["Heptane", "Methanol", "PMMA"]  # no Decane (FLEX-2)
    assert list(grid.columns) == ["18%", "21%", "22%"]  # 21.5-22.1 -> middle 21.8 -> 22
    assert grid.loc["Heptane", "21%"] == 2
    assert grid.loc["Methanol", "21%"] == 0


def test_only_flex2_rows_give_an_empty_grid():
    assert material_oxygen_test_counts(ROWS[ROWS["experiment"] == "FLEX-2"]).empty
