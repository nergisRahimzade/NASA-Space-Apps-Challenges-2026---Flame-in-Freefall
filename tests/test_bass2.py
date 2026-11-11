"""Day 16 (FIF-D16-DAT): BASS-II cleaning rules, checked on the cells they were written for.

Most BASS-II cells are notes typed during the test. Each rule is checked on real cells from
data/raw/PSI-25_Experimental table_BASS-II.csv. Rules and reasons: data_notes.md section 13."""

import pandas as pd
import pytest

from flame_in_freefall.clean_tables import (
    bass2_date,
    bass2_flows,
    bass2_lowest_flow_unknown,
    bass2_material,
    bass2_outcome,
    bass2_thickness_mm,
    clean_bass2,
)


@pytest.fixture(scope="module")
def bass2() -> pd.DataFrame:
    return clean_bass2().set_index("test_id")


def test_every_test_kept_once(bass2):
    assert len(bass2) == 129 and bass2.index.is_unique


@pytest.mark.parametrize(
    ("text", "material"),
    [
        ("100 micron PMMA film   2 cm wide", "PMMA film"),
        ("200 micron  2 cm wide ", "PMMA film"),  # same series, PMMA not repeated
        ("3 mm thick PMMA 1 sided    2 cm wide", "PMMA slab"),
        ('1/4" clear rod', "PMMA rod"),  # O5 says "clear PMMA rod"
        ('3/8" black rod', "Black rod"),  # never named: not guessed
        ("1/4 blac rod", "Black rod"),  # typo in the raw file
        ("2 cm Sibal   moved igniter", "Cotton-Fiberglass (SIBAL)"),  # Saffire-II spelling
        ("4 cm spherical section", "Spherical section"),
        ("Nomex natural (nomex III)", "Nomex"),
        ("Japan Wax candle", "Japan wax candle"),
    ],
)
def test_material(text, material):
    assert bass2_material(text) == material


def test_unknown_material_fails_loudly():
    with pytest.raises(ValueError, match="unknown BASS-II sample"):
        bass2_material("aluminium foil")


@pytest.mark.parametrize(
    ("text", "mm"),
    [
        ("100 micron PMMA film   2 cm wide", 0.1),
        ("2 cm   0.2 mm PMMA film", 0.2),
        ('1/4" clear rod', 6.35),  # rods: diameter
        ('0.5" black rod', 12.7),
        ("2 cm SIBAL", None),
    ],
)
def test_thickness(text, mm):
    got = bass2_thickness_mm(text)
    assert pd.isna(got) if mm is None else got == pytest.approx(mm)


@pytest.mark.parametrize(
    ("air", "speeds"),
    [
        ("5  3  2   ext", [5, 3, 2]),
        ("3  0.5 pot   0.4 pot", [3]),  # fan pot settings aren't speeds
        ("5   3    pot 0.4", [5, 3]),
        ("5   pots 0.4   0.36   0.32   off", [5]),
        ("5  10  5   2   0 (49   62   49   44   42)", [5, 10, 5, 2, 0]),  # brackets: fan
        ("49  44  42  41  41  40.5 (5   2   0)", [5, 2, 0]),  # O13a: swapped
        ("49   5 cm/s", [5]),  # over 40 cm/s is a fan reading (report: tunnel max 40)
        ("6   53", [6]),
        ("no ign at any flow", []),
    ],
)
def test_flows(air, speeds):
    assert bass2_flows(air) == speeds


@pytest.mark.parametrize(
    ("air", "unknown"),
    [
        ("5 down to ext", True),
        ("2   <1", True),
        ("5   pots 0.4   0.36   0.32   off", True),  # turned below 5 on the fan
        ("5   2.5 (1.15   .5   .35)", True),  # pot values in brackets
        ("incr to 28", True),  # start not written
        ("5  3  2   ext", False),
        ("5  10  5   2   0 (49   62   49   44   42)", False),
        ("4 incr to 26.5", False),
    ],
)
def test_lowest_flow_unknown(air, unknown):
    assert bass2_lowest_flow_unknown(air) is unknown


@pytest.mark.parametrize(
    ("fan", "air", "outcome"),
    [
        ("pots 1.4   3   0.9   0.7", "no ign at any flow", "No ignition"),
        ("47 (pot 1.05)   incr to pot 6.0", "10   blowoff", "Blowoff"),
        ("53   and down", "5 down to ext", "Extinction"),
        ("5   .36  .32  .31  .305   out .275", "see fan", "Extinction"),
        ("48   62   75", "5   would not stay lit   10   15 ibid", "Extinction"),
        ("80   59   55", "9   5   4", None),  # nothing said: unknown, not "kept burning"
    ],
)
def test_outcome(fan, air, outcome):
    assert bass2_outcome(fan, air) == outcome


def test_year_typo_is_fixed():
    # T9 and T18: 6/24/2018, but their day-of-year (175) is 2014-06-24.
    assert bass2_date("6/24/2018") == "2014-06-24"
    assert bass2_date("2/26/2016") == "2016-02-26"  # 3 real 2016 tests


def test_cleaned_rows(bass2):
    outcomes = bass2["outcome"].value_counts().to_dict()
    assert outcomes == {"Extinction": 20, "Blowoff": 7, "No ignition": 1}
    assert bass2["outcome"].isna().sum() == 101  # nothing typed about how the flame ended
    assert bass2["oxygen_pct_min"].between(13.6, 22.2).all()
    assert bass2["flow_cm_s_max"].max() <= 40
    # Final O2 glitches (B2 1.6, P22a 0.6, P22b 39.1, T28a 0.9, T28b 40.4) are blanked.
    assert bass2.loc[["B2", "P22a", "P22b", "T28a", "T28b"], "oxygen_final_pct"].isna().all()
    assert bass2.loc["B14", ["flow_cm_s_min", "flow_cm_s_max"]].tolist() == [2.0, 5.0]
