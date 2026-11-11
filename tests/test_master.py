"""FIF-D09-DAT: master.csv loads and has the columns from data_notes.md."""

import pandas as pd
import pytest

from flame_in_freefall.build_master import MASTER, MASTER_COLUMNS, build_master
from flame_in_freefall.clean_tables import clean_bass2, clean_flex, clean_flex2, clean_saffire2


@pytest.fixture(scope="module")
def master() -> pd.DataFrame:
    # Built from the raw files, so the test does not depend on data/clean/ being up to date.
    return build_master([clean_flex2(), clean_saffire2(), clean_flex(), clean_bass2()])


def test_columns_and_row_counts(master):
    assert list(master.columns) == MASTER_COLUMNS
    counts = master["experiment"].value_counts().to_dict()
    assert counts == {"FLEX-2": 8, "Saffire-II": 9, "FLEX": 273, "BASS-II": 129}


def test_every_row_has_material_oxygen_and_flow(master):
    for col in ("material", "oxygen_pct_min", "oxygen_pct_max"):
        assert master[col].notna().all(), col
    # BASS-II's airflow comes from typed notes: the lowest speed is empty when the air was
    # turned down further than the notes say, and 6 tests give no speed at all.
    others = master[master["experiment"] != "BASS-II"]
    for col in ("flow_cm_s_min", "flow_cm_s_max"):
        assert others[col].notna().all(), col


def test_empty_where_a_source_has_no_data(master):
    by_exp = master.groupby("experiment")
    assert by_exp.get_group("Saffire-II")["pressure_kpa_min"].isna().all()
    assert by_exp.get_group("FLEX")["spread_rate_mm_s"].isna().all()
    assert by_exp.get_group("FLEX-2")["outcome"].isna().all()
    assert by_exp.get_group("FLEX")["outcome"].notna().all()


def test_every_row_has_a_material_category(master):
    assert master["material_category"].notna().all()
    by_material = master.groupby("material")["material_category"].first()
    assert by_material["Heptane"] == "hydrocarbon"
    assert by_material["Propanol (80%) Glycerol (20%)"] == "alcohol"
    assert by_material["PMMA"] == "plastic"
    assert by_material["Cotton-Fiberglass (SIBAL)"] == "fabric"


def test_unknown_material_has_no_category_and_fails_the_build():
    new_fuel = pd.DataFrame({"experiment": ["FLEX"], "material": ["Kerosene"]})
    with pytest.raises(ValueError, match="Kerosene"):
        build_master([new_fuel])


def test_spread_rate_per_flow_only_where_spread_and_one_airflow(master):
    has_ratio = master["spread_rate_per_flow"].notna()
    # Only the 2 SIBAL samples have a spread rate; Saffire-II airflow is 20 cm/s = 200 mm/s.
    assert has_ratio.sum() == 2
    sibal = master[has_ratio]
    assert (sibal["material"] == "Cotton-Fiberglass (SIBAL)").all()
    assert sibal["spread_rate_per_flow"].tolist() == pytest.approx([2.1 / 200, 2.6 / 200])


def test_spread_rate_per_flow_empty_for_no_airflow_or_a_range():
    rows = pd.DataFrame(
        {
            "experiment": ["FLEX", "FLEX-2"],
            "material": ["Heptane", "Heptane"],
            "flow_cm_s_min": [0.0, 0.1],
            "flow_cm_s_max": [0.0, 5.0],
            "spread_rate_mm_s": [1.0, 1.0],  # made up, so only the airflow decides
        }
    )
    assert build_master([rows])["spread_rate_per_flow"].isna().all()


def test_suppressant_comes_from_the_gas_mix(master):
    # FIF-D16-DAT: FLEX replaced some nitrogen with CO2 or helium; Saffire-II burned in air.
    by_exp = master.groupby("experiment")
    flex = by_exp.get_group("FLEX")
    assert flex["suppressant"].value_counts().to_dict() == {"CO2": 123, "none": 100, "He": 50}
    assert flex.loc[flex["suppressant"] == "none", "suppressant_pct"].eq(0).all()
    assert flex.loc[flex["suppressant"] != "none", "suppressant_pct"].between(5, 70).all()
    for plain_air in ("Saffire-II", "BASS-II"):  # BASS-II lowered O2 with nitrogen
        rows = by_exp.get_group(plain_air)
        assert rows["suppressant"].eq("none").all() and rows["suppressant_pct"].eq(0).all()
    # FLEX-2's table says "O2/N2 or O2/He" for every fuel, so it stays empty.
    flex2 = by_exp.get_group("FLEX-2")
    assert flex2["suppressant"].isna().all() and flex2["suppressant_pct"].isna().all()


def test_suppressant_pct_is_the_added_gas():
    rows = pd.DataFrame(
        {
            "experiment": ["FLEX"] * 3,
            "material": ["Heptane"] * 3,
            "co2_pct": [15.0, 0.0, 0.0],
            "helium_pct": [0.0, 40.0, 0.0],
        }
    )
    master = build_master([rows])
    assert master["suppressant"].tolist() == ["CO2", "He", "none"]
    assert master["suppressant_pct"].tolist() == [15.0, 40.0, 0.0]


def test_a_test_with_both_gases_fails_loudly():
    both = pd.DataFrame(
        {"experiment": ["FLEX"], "material": ["Heptane"], "co2_pct": [10.0], "helium_pct": [10.0]}
    )
    with pytest.raises(ValueError, match="both CO2 and helium"):
        build_master([both])


def test_saved_master_loads_and_matches_a_fresh_build(master):
    saved = pd.read_csv(MASTER)
    pd.testing.assert_frame_equal(saved, master, check_dtype=False)
