"""Day 9 (FIF-D09-DAT): combine the clean tables into one data/master.csv.
Day 11 (FIF-D11-DAT): add two helpful columns, material_category and spread_rate_per_flow.
Day 16 (FIF-D16-DAT): add suppressant and suppressant_pct, the fire-suppressing gas in the mix,
and BASS-II (data/clean/bass2.csv) as the 4th experiment.

Columns follow data_notes.md sections 2 and 7. Run from the repo root (after clean_tables):
    uv run python -m flame_in_freefall.build_master
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "clean"
MASTER = ROOT / "data" / "master.csv"

# Order of experiments (data_notes.md): FLEX-2, Saffire-II, FLEX, then BASS-II (Day 16).
CLEAN_FILES = ("flex2.csv", "saffire2.csv", "flex.csv", "bass2.csv")

MASTER_COLUMNS = [
    "experiment",
    "material",
    "material_category",  # Day 11
    "oxygen_pct_min",
    "oxygen_pct_max",
    "pressure_kpa_min",
    "pressure_kpa_max",
    "flow_cm_s_min",
    "flow_cm_s_max",
    "suppressant",  # Day 16
    "suppressant_pct",  # Day 16
    "spread_rate_mm_s",
    "spread_rate_per_flow",  # Day 11
    "outcome",
]

NUMBER_COLUMNS = [
    "oxygen_pct_min",
    "oxygen_pct_max",
    "pressure_kpa_min",
    "pressure_kpa_max",
    "flow_cm_s_min",
    "flow_cm_s_max",
    "suppressant_pct",
    "spread_rate_mm_s",
    "spread_rate_per_flow",
]

# Day 11: the group each material belongs to, so charts can compare like with like.
# Liquid fuels (FLEX, FLEX-2 droplets) are split by chemistry, solids (Saffire-II sheets)
# by what the material is. Mixtures go with their parts (Propanol + Glycerol are both
# alcohols, Heptane + IsoOctane both hydrocarbons). Descriptions: docs/reports/.
MATERIAL_CATEGORY = {
    # Liquid fuels
    "Heptane": "hydrocarbon",
    "IsoOctane": "hydrocarbon",
    "n-Octane": "hydrocarbon",
    "Decane": "hydrocarbon",
    "Heptane (50%) IsoOctane (50%)": "hydrocarbon",
    "Methanol": "alcohol",
    "Ethanol": "alcohol",
    "Propanol (95%) Glycerol (5%)": "alcohol",
    "Propanol (80%) Glycerol (20%)": "alcohol",
    # Solid materials
    "PMMA": "plastic",  # acrylic (Plexiglas)
    "Cotton-Fiberglass (SIBAL)": "fabric",
    "Silicone": "silicone",  # silicone rubber sheet
    "PMMA & Nomex": "plastic + fabric",  # Nomex is a fire-resistant fabric
    # BASS-II solids (Day 16). Black rods and spherical sections never name their
    # material (table or report), so their category is unknown, not guessed.
    "PMMA film": "plastic",
    "PMMA slab": "plastic",
    "PMMA rod": "plastic",
    "Black rod": "unknown",
    "Spherical section": "unknown",
    "Nomex": "fabric",
    "Japan wax candle": "wax",
}

MM_PER_CM = 10

# Day 16: experiments that burned in plain air, so no suppressant was added. The Saffire-II
# report says air was drawn through the flow duct. BASS-II lowered oxygen by adding
# nitrogen (report); its CO2 readings (0.2-2%) are cabin air and burning, not added gas.
# FLEX-2 is not here: its table says "O2/N2 or O2/He" without saying which fuel used
# which, so its suppressant stays empty.
PLAIN_AIR = {"Saffire-II", "BASS-II"}


def material_category(material: pd.Series) -> pd.Series:
    """Look up each material's category. A material missing from MATERIAL_CATEGORY is an
    error, so a new material can't end up with a silently empty category."""
    unknown = sorted(set(material) - set(MATERIAL_CATEGORY))
    if unknown:
        raise ValueError(f"no material_category for {unknown}: add them to MATERIAL_CATEGORY")
    return material.map(MATERIAL_CATEGORY)


def spread_rate_per_flow(master: pd.DataFrame) -> pd.Series:
    """Flame spread rate divided by airflow speed, both in mm/s, so it has no unit.

    0.01 means the flame moves 1/100th as fast as the air blowing past it. Unlike the raw
    spread rate, it can be compared between tests run at different airflow speeds.
    Left empty when there is no spread rate, no airflow (FLEX), or the airflow is a range
    (FLEX-2), because a range doesn't give one number to divide by."""
    flow = master["flow_cm_s_min"]
    one_flow = (flow == master["flow_cm_s_max"]) & (flow > 0)
    ratio = master["spread_rate_mm_s"] / (flow * MM_PER_CM)
    return ratio.where(one_flow).round(4)


def add_suppressant(table: pd.DataFrame) -> pd.DataFrame:
    """Add suppressant ("none", "CO2" or "He") and suppressant_pct (its share of the gas, %).

    FLEX replaced some nitrogen with CO2 or helium to make flames go out more easily, and the
    clean table has their shares (co2_pct, helium_pct). Experiments in PLAIN_AIR get "none" and
    0; any other experiment stays empty, because its table doesn't say."""
    table = table.copy()
    if {"co2_pct", "helium_pct"} <= set(table.columns):
        co2, helium = table["co2_pct"], table["helium_pct"]
        # Never happens in FLEX; fail loudly rather than pick one of the two.
        if (co2.gt(0) & helium.gt(0)).any():
            raise ValueError("a test has both CO2 and helium: decide how to label it")
        table["suppressant"] = np.select([co2.gt(0), helium.gt(0)], ["CO2", "He"], "none")
        table["suppressant_pct"] = co2.where(co2.gt(0), helium)
    elif set(table["experiment"]) <= PLAIN_AIR:
        table["suppressant"] = "none"
        table["suppressant_pct"] = 0.0
    return table


def build_master(tables: list[pd.DataFrame]) -> pd.DataFrame:
    """Stack the clean tables, keep only the master columns and add the Day 11 columns.

    A column a table does not have is left empty (for example Saffire-II has no
    pressure, FLEX has no spread rate, only FLEX has an outcome)."""
    tables = [add_suppressant(t) for t in tables]
    master = pd.concat([t.reindex(columns=MASTER_COLUMNS) for t in tables], ignore_index=True)
    master = master.astype({c: "float64" for c in NUMBER_COLUMNS})
    master["material_category"] = material_category(master["material"])
    master["spread_rate_per_flow"] = spread_rate_per_flow(master)
    return master


def load_clean_tables(folder: Path = CLEAN) -> list[pd.DataFrame]:
    return [pd.read_csv(folder / name) for name in CLEAN_FILES]


def main() -> None:
    master = build_master(load_clean_tables())
    master.to_csv(MASTER, index=False)
    print(f"master.csv: {len(master)} rows x {master.shape[1]} columns -> data/master.csv")
    print(master["experiment"].value_counts(sort=False).to_string())


if __name__ == "__main__":
    main()
