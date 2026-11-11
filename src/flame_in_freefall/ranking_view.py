"""Day 13 (FE): read data/ranking.csv (FIF-D13-DAT) for the riskiness charts.

Each experiment is ranked on its own measure (data_notes.md section 9), so the app draws one
chart per experiment and never puts the two on one axis:
- Saffire-II: average flame spread in mm/s, one bar per material
- FLEX: share of finished tests where the flame kept burning, by fuel and oxygen level"""

from pathlib import Path

import pandas as pd

RANKING_CSV = Path(__file__).resolve().parents[2] / "data" / "ranking.csv"

# Plain-word axis labels for each value of the risk_basis column.
BASIS_LABELS = {
    "burn_spread_mm_s_mean": "Average flame spread (mm/s)",
    "kept_burning_share": "Share of tests where the flame kept burning",
}


def load_ranking(path: str | Path = RANKING_CSV) -> pd.DataFrame:
    """The ranking table, or an empty table if the file hasn't been built."""
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame()


def filter_ranking(
    ranking: pd.DataFrame,
    experiment: str | None = None,
    material: str | None = None,
    oxygen_min: float | None = None,
    oxygen_max: float | None = None,
) -> pd.DataFrame:
    """The rows matching the sidebar filters. None means "don't filter on this"."""
    if ranking.empty:
        return ranking
    keep = pd.Series(True, index=ranking.index)
    if experiment is not None:
        keep &= ranking["experiment"] == experiment
    if material is not None:
        keep &= ranking["material"] == material
    if oxygen_min is not None:
        keep &= ranking["oxygen_pct"] >= oxygen_min
    if oxygen_max is not None:
        keep &= ranking["oxygen_pct"] <= oxygen_max
    return ranking[keep]


def axis_label(rows: pd.DataFrame) -> str:
    """The value axis label for one experiment's rows, from their risk_basis."""
    basis = rows["risk_basis"].iloc[0]
    return BASIS_LABELS.get(basis, basis)
