"""Day 9 (FIF-D09-DAT): combine the clean tables into one data/master.csv.

Columns follow data_notes.md section 2. Run from the repo root (after clean_tables):
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
    "oxygen_pct_min",
    "oxygen_pct_max",
    "pressure_kpa_min",
    "pressure_kpa_max",
    "flow_cm_s_min",
    "flow_cm_s_max",
    "spread_rate_mm_s",
    "outcome",
]


def build_master(tables: list[pd.DataFrame]) -> pd.DataFrame:
    """Stack the clean tables and keep only the master columns.

    A column a table does not have is left empty (for example Saffire-II has no
    pressure, FLEX has no spread rate, only FLEX has an outcome)."""
    master = pd.concat([t.reindex(columns=MASTER_COLUMNS) for t in tables], ignore_index=True)
    return master.astype({c: "float64" for c in MASTER_COLUMNS[2:9]})


def load_clean_tables(folder: Path = CLEAN) -> list[pd.DataFrame]:
    return [pd.read_csv(folder / name) for name in CLEAN_FILES]


def main() -> None:
    master = build_master(load_clean_tables())
    master.to_csv(MASTER, index=False)
    print(f"master.csv: {len(master)} rows x {master.shape[1]} columns -> data/master.csv")
    print(master["experiment"].value_counts(sort=False).to_string())


if __name__ == "__main__":
    main()
