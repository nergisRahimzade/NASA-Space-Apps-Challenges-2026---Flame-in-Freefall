"""FIF-D08-DAT: the cleaned tables have no odd values."""

import math

import pandas as pd
import pytest

from flame_in_freefall.clean_tables import (
    clean_flex,
    clean_flex2,
    clean_saffire2,
    first_number,
    numbers_in,
    thickness_mm,
    tidy_material,
)

RANGE_COLUMNS = ("oxygen_pct", "pressure_kpa", "flow_cm_s")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("0.17; 0.21;0.25; 0.3", [0.17, 0.21, 0.25, 0.3]),
        ("0.1 - 5", [0.1, 5.0]),
        ("22.1 to 22.0", [22.1, 22.0]),
        ("Note 4", []),
        ("~ 10 cm (note 3)", [10.0]),
        ("�", []),
    ],
)
def test_numbers_in(text, expected):
    assert numbers_in(text) == expected


def test_first_number_placeholders_become_nan():
    for text in ("n/a", "n/a (Nomex)", "Insignificant", "Note 4", "�"):
        assert math.isnan(first_number(text))
    assert first_number("~6") == 6.0
    assert first_number("20 cm/s") == 20.0


def test_thickness_units_and_typo():
    assert thickness_mm("1 cm") == 10.0
    assert thickness_mm("037 mm") == 0.37
    assert math.isnan(thickness_mm("See Fig. 5"))


def test_material_has_one_spelling():
    assert tidy_material("Heptane (pure)") == "Heptane"
    assert tidy_material("Heptane (50%) IsoOctane (50%) (mixture)") == (
        "Heptane (50%) IsoOctane (50%)"
    )


@pytest.fixture(scope="module", params=["flex2", "saffire2", "flex"])
def table(request) -> pd.DataFrame:
    return {"flex2": clean_flex2, "saffire2": clean_saffire2, "flex": clean_flex}[request.param]()


def test_columns_are_snake_case(table):
    for col in table.columns:
        assert col == col.strip().lower().replace(" ", "_"), col


def test_no_missing_material(table):
    assert table["material"].notna().all()


def test_ranges_are_numeric_and_ordered(table):
    for base in RANGE_COLUMNS:
        lo, hi = f"{base}_min", f"{base}_max"
        if lo not in table:
            continue
        assert pd.api.types.is_numeric_dtype(table[lo]), lo
        both = table[[lo, hi]].dropna()
        assert (both[lo] <= both[hi]).all(), base


def test_oxygen_is_a_percent(table):
    assert table["oxygen_pct_min"].between(0, 100).all()
    assert table["oxygen_pct_max"].between(0, 100).all()


def test_row_counts():
    assert len(clean_flex2()) == 8
    assert len(clean_saffire2()) == 9  # footnote and flow-visualization rows dropped
    assert len(clean_flex()) == 273  # 274 minus the repeated 193F001


def test_flex_details():
    flex = clean_flex()
    assert flex["test_id"].is_unique
    assert set(flex["outcome"]) == {"Extinction", "Completion", "Disruption"}
    assert (flex["pressure_kpa_min"].dropna() > 0).all()  # 0 mmHg became missing
    assert (flex["flow_cm_s_min"] == 0).all()


def test_saffire_material_filled_down():
    saffire = clean_saffire2().set_index("sample_id")
    assert saffire.loc["2-6", "material"] == "Cotton-Fiberglass (SIBAL)"
    assert saffire.loc["2-9", "material"] == "PMMA"
