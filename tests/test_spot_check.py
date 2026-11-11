"""Day 14 (DAT): spot-check the data against the numbers the reports give.

Each test first checks that the report really says it (so a changed report can't leave a stale
test), then checks the saved tables. Results and reasons: data_notes.md section 10."""

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs" / "reports"
MASTER = pd.read_csv(ROOT / "data" / "master.csv")
FLEX = pd.read_csv(ROOT / "data" / "clean" / "flex.csv")
ATM_KPA = 101.325


def report(name: str) -> str:
    # Squash whitespace so a line break inside a phrase doesn't matter.
    return " ".join((REPORTS / name).read_text(encoding="utf-8").split())


def rows(experiment: str) -> pd.DataFrame:
    return MASTER[MASTER["experiment"] == experiment]


def test_flex2_pressure_matches_the_report():
    assert "varied in pressure between 0.5 atm to 3.0 atm" in report("flex2_abstract.txt")
    flex2 = rows("FLEX-2")
    # Stored to 3 decimals: 0.5 atm = 50.6625 kPa is saved as 50.662.
    assert flex2["pressure_kpa_min"].tolist() == pytest.approx([0.5 * ATM_KPA] * 8, abs=0.001)
    assert flex2["pressure_kpa_max"].tolist() == pytest.approx([3.0 * ATM_KPA] * 8, abs=0.001)


def test_flex2_oxygen_levels_sit_inside_the_report_range():
    # The report gives the chamber's range (0.1-0.4); the table lists the 4 levels used.
    assert "O2 concentration between 0.1 to 0.4 mole fraction" in report("flex2_abstract.txt")
    flex2 = rows("FLEX-2")
    assert flex2["oxygen_pct_min"].eq(17).all() and flex2["oxygen_pct_max"].eq(30).all()
    assert flex2["oxygen_pct_min"].ge(10).all() and flex2["oxygen_pct_max"].le(40).all()


def test_flex_droplets_are_about_3_mm():
    assert "Select a smaller droplet size (≈ 3 mm)" in report("flex_abstract.txt")
    assert FLEX["droplet_diameter_mm"].median() == pytest.approx(3.0, abs=0.1)


def test_flex_pressures_outside_the_report_range_are_the_co2_series():
    # The report gives 0.5-1.5 atm for the LOI tests. The only tests above that are the
    # 9 run in 70% CO2, a separate high-pressure series (2.0-3.05 atm).
    assert "Select the test pressure (0.5 − 1.5 atm) for the LOI tests" in report(
        "flex_abstract.txt"
    )
    high = FLEX[FLEX["pressure_kpa_min"] > 1.5 * ATM_KPA]
    assert len(high) == 9
    assert high["co2_pct"].eq(70).all()
    assert FLEX["pressure_kpa_min"].dropna().ge(0.5 * ATM_KPA).all()


def test_flex_suppressant_column_is_co2():
    # The report names CO2 and He as suppressants; the raw "CO" header lost its subscript.
    assert "CO2, He, and SF6" in report("flex_abstract.txt")
    assert {"co2_pct", "helium_pct"} <= set(FLEX.columns)
    assert "co_pct" not in FLEX.columns
    assert FLEX["co2_pct"].max() == 70  # 70% carbon monoxide would make no sense


def test_saffire2_samples_and_airflow_match_the_report():
    text = report("saffire2_abstract.txt")
    assert "a sample card that contains 9 samples" in text
    assert "air flow velocity of either 20 or 30 cm/s" in text
    saffire = rows("Saffire-II")
    assert len(saffire) == 9
    # The table runs all 9 at 20 cm/s; none of them at 30.
    assert saffire["flow_cm_s_min"].eq(20).all() and saffire["flow_cm_s_max"].eq(20).all()


def test_saffire2_materials_are_the_reports():
    assert "SIBAL, silicone, structure PMMA, flat PMMA, and PMMA with Nomex" in report(
        "saffire2_abstract.txt"
    )
    counts = rows("Saffire-II")["material"].value_counts().to_dict()
    # Structure and flat PMMA are one sample each, both labelled "PMMA" (data_notes.md section 10).
    assert counts == {
        "Silicone": 4,
        "Cotton-Fiberglass (SIBAL)": 2,
        "PMMA": 2,
        "PMMA & Nomex": 1,
    }
