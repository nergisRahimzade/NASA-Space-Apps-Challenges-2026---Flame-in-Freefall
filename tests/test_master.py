"""FIF-D09-DAT: master.csv loads and has the columns from data_notes.md."""

import pandas as pd
import pytest

from flame_in_freefall.build_master import MASTER, MASTER_COLUMNS, build_master
from flame_in_freefall.clean_tables import clean_flex, clean_flex2, clean_saffire2


@pytest.fixture(scope="module")
def master() -> pd.DataFrame:
    # Built from the raw files, so the test does not depend on data/clean/ being up to date.
    return build_master([clean_flex2(), clean_saffire2(), clean_flex()])


def test_columns_and_row_counts(master):
    assert list(master.columns) == MASTER_COLUMNS
    counts = master["experiment"].value_counts().to_dict()
    assert counts == {"FLEX-2": 8, "Saffire-II": 9, "FLEX": 273}


def test_every_row_has_material_oxygen_and_flow(master):
    for col in ("material", "oxygen_pct_min", "oxygen_pct_max", "flow_cm_s_min", "flow_cm_s_max"):
        assert master[col].notna().all(), col


def test_empty_where_a_source_has_no_data(master):
    by_exp = master.groupby("experiment")
    assert by_exp.get_group("Saffire-II")["pressure_kpa_min"].isna().all()
    assert by_exp.get_group("FLEX")["spread_rate_mm_s"].isna().all()
    assert by_exp.get_group("FLEX-2")["outcome"].isna().all()
    assert by_exp.get_group("FLEX")["outcome"].notna().all()


def test_saved_master_loads_and_matches_a_fresh_build(master):
    saved = pd.read_csv(MASTER)
    pd.testing.assert_frame_equal(saved, master, check_dtype=False)
