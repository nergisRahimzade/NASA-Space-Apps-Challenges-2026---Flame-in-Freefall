"""Day 17 (FE): one filter state that every part of the page reads.

The sidebar builds a single Filters value. Search, the table and every chart take it from
there, so they always show the same experiment, material and oxygen range (FIF-D17-FE)."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

ALL = "All"


@dataclass(frozen=True)
class Filters:
    """What the sidebar has picked. None means "all" for experiment and material."""

    experiment: str | None
    material: str | None
    oxygen_min: float
    oxygen_max: float

    def table_filters(self) -> dict:
        """The same choice in the shape get_table() takes (docs/contract.md)."""
        out = {"oxygen_min": self.oxygen_min, "oxygen_max": self.oxygen_max}
        if self.experiment:
            out["experiment"] = self.experiment
        if self.material:
            out["material"] = self.material
        return out

    def describe(self) -> str:
        """One line for the top of the page, e.g. "FLEX · Heptane · 15–30% oxygen"."""
        return " · ".join(
            [
                self.experiment or "All experiments",
                self.material or "all materials",
                f"{self.oxygen_min:g}–{self.oxygen_max:g}% oxygen",
            ]
        )


def from_choices(experiment: str, material: str, oxygen: tuple[float, float]) -> Filters:
    """Turn the sidebar's widget values ("All" = no filter) into a Filters."""
    return Filters(
        experiment=None if experiment == ALL else experiment,
        material=None if material == ALL else material,
        oxygen_min=float(oxygen[0]),
        oxygen_max=float(oxygen[1]),
    )


def material_options(rows: pd.DataFrame, experiment: str) -> list[str]:
    """The materials to offer for the chosen experiment, so the Material list never offers a
    choice that would empty every chart (e.g. PMMA with FLEX)."""
    if experiment != ALL:
        rows = rows[rows["experiment"] == experiment]
    return [ALL, *sorted(rows["material"].unique())]


def oxygen_level(rows: pd.DataFrame) -> pd.Series:
    """Each row's oxygen as a whole percent: the middle of its min and max, 0.5 rounding up.
    The same rule Data used for ranking.csv (build_ranking.oxygen_level)."""
    middle = (rows["oxygen_pct_min"] + rows["oxygen_pct_max"]) / 2
    return np.floor(middle + 0.5)


def material_oxygen_test_counts(table: pd.DataFrame) -> pd.DataFrame:
    """How many tests ran for each material at each oxygen level, as a grid for a heatmap.

    Only experiments whose rows are real tests are counted (FLEX and Saffire-II). FLEX-2's rows
    are planned ranges, one per fuel, so a count for them would be misleading."""
    tests = table[table["experiment"] != "FLEX-2"]
    if tests.empty:
        return pd.DataFrame()
    counts = (
        tests.assign(oxygen=oxygen_level(tests))
        .groupby(["material", "oxygen"])
        .size()
        .unstack(fill_value=0)
        .sort_index(axis=1)
    )
    counts.columns = [f"{o:g}%" for o in counts.columns]
    return counts
