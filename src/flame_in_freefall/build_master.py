"""Day 9 (FIF-D09-DAT): combine the clean tables into one data/master.csv.
Day 11 (FIF-D11-DAT): add two helpful columns, material_category and spread_rate_per_flow.

Columns follow data_notes.md sections 2 and 7. Run from the repo root (after clean_tables):
    uv run python -m flame_in_freefall.build_master
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "clean"
MASTER = ROOT / "data" / "master.csv"

# Order of experiments (data_notes.md): FLEX-2, Saffire-II, FLEX.
CLEAN_FILES = ("flex2.csv", "saffire2.csv", "flex.csv")

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
}

MM_PER_CM = 10


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


def build_master(tables: list[pd.DataFrame]) -> pd.DataFrame:
    """Stack the clean tables, keep only the master columns and add the Day 11 columns.

    A column a table does not have is left empty (for example Saffire-II has no
    pressure, FLEX has no spread rate, only FLEX has an outcome)."""
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
