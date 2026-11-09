"""Day 13 (FIF-D13-DAT): riskiness ranking table, saved as data/ranking.csv.

Groups the tests by material and oxygen level and works out, for each group, how fast the
flame spread and how often it kept burning. Each group then gets a rank within its own
experiment (1 = riskiest). Rules and reasons: data_notes.md section 9.

Run from the repo root (after build_master):
    uv run python -m flame_in_freefall.build_ranking
"""

from pathlib import Path

import numpy as np
import pandas as pd

from flame_in_freefall.build_master import CLEAN, MASTER, MM_PER_CM

ROOT = Path(__file__).resolve().parents[2]
RANKING = ROOT / "data" / "ranking.csv"
SAFFIRE2_CLEAN = CLEAN / "saffire2.csv"

GROUP_KEYS = ["experiment", "material", "material_category", "oxygen_pct"]

RANKING_COLUMNS = [
    *GROUP_KEYS,
    "tests",
    # Measured spread rate (master.csv spread_rate_mm_s). Only SIBAL has one.
    "spread_rate_n",
    "spread_rate_mm_s_min",
    "spread_rate_mm_s_mean",
    "spread_rate_mm_s_max",
    # Average spread over the whole burn = burn length / burn time (Saffire-II only).
    "burn_spread_mm_s_mean",
    # How FLEX tests ended.
    "completion",
    "extinction",
    "disruption",
    "kept_burning_share",
    # The ranking itself.
    "risk_basis",
    "risk_value",
    "risk_rank",
]

# What decides the rank in each experiment. Droplets and sheets can't be put on one scale
# (one has a spread speed, the other only "went out or not"), so each is ranked on its own.
RISK_BASIS = {
    "Saffire-II": "burn_spread_mm_s_mean",
    "FLEX": "kept_burning_share",
}

EXPERIMENT_ORDER = ["Saffire-II", "FLEX"]


def oxygen_level(table: pd.DataFrame) -> pd.Series:
    """The oxygen level a row is grouped under: the middle of its min/max, to the nearest
    whole percent (0.5 rounds up). Saffire-II's 21.5-22.1% all become 22, which is fine:
    the report calls them approximate."""
    middle = (table["oxygen_pct_min"] + table["oxygen_pct_max"]) / 2
    return np.floor(middle + 0.5)


def burn_spread_mm_s(saffire2: pd.DataFrame) -> pd.Series:
    """Average flame spread over the whole burn: microgravity burn length / burn time, in mm/s.

    A burn length of 0 means the flame never spread, so the speed is 0 even though the burn
    time is empty ('Insignificant'). For SIBAL, which also has a measured spread rate, this
    gives 2.0 and 2.5 mm/s against a measured 2.1 and 2.6, so it is a fair stand-in."""
    length_mm = saffire2["burn_length_cm"] * MM_PER_CM
    speed = length_mm / saffire2["burn_time_s"]
    return speed.mask(saffire2["burn_length_cm"] == 0, 0.0)


def _saffire_burn_spread(saffire2: pd.DataFrame) -> pd.DataFrame:
    rows = saffire2.assign(oxygen_pct=oxygen_level(saffire2), burn=burn_spread_mm_s(saffire2))
    keys = ["experiment", "material", "oxygen_pct"]
    return rows.groupby(keys, as_index=False).agg(burn_spread_mm_s_mean=("burn", "mean"))


def build_ranking(master: pd.DataFrame, saffire2: pd.DataFrame) -> pd.DataFrame:
    """One row per (experiment, material, oxygen level), ranked within each experiment.

    `saffire2` is the clean Saffire-II table, which has the burn length and burn time that
    master.csv leaves out. Groups with no result at all (no spread rate, no burn length, no
    outcome) are dropped. That removes FLEX-2, whose rows are planned ranges, not results."""
    rows = master.assign(oxygen_pct=oxygen_level(master))
    for word in ("Completion", "Extinction", "Disruption"):
        rows[word.lower()] = (rows["outcome"] == word).astype(int)

    table = rows.groupby(GROUP_KEYS, as_index=False).agg(
        tests=("material", "size"),
        spread_rate_n=("spread_rate_mm_s", "count"),
        spread_rate_mm_s_min=("spread_rate_mm_s", "min"),
        spread_rate_mm_s_mean=("spread_rate_mm_s", "mean"),
        spread_rate_mm_s_max=("spread_rate_mm_s", "max"),
        completion=("completion", "sum"),
        extinction=("extinction", "sum"),
        disruption=("disruption", "sum"),
        outcomes=("outcome", "count"),
    )
    # A group with no outcome at all (Saffire-II has no outcome column) gets empty counts,
    # not 0, so it doesn't read as "0 tests went out".
    for col in ("completion", "extinction", "disruption"):
        table[col] = table[col].astype("Int64").mask(table["outcomes"] == 0)
    table = table.merge(
        _saffire_burn_spread(saffire2), on=["experiment", "material", "oxygen_pct"], how="left"
    )

    # Share of the tests that finished (Disruption = cut short, so left out) in which the
    # flame burned until the fuel was gone instead of going out on its own.
    finished = (table["completion"] + table["extinction"]).astype(float)
    completed = table["completion"].astype(float)
    table["kept_burning_share"] = (completed / finished.where(finished > 0)).round(3)

    has_result = (
        table["spread_rate_n"].gt(0) | table["burn_spread_mm_s_mean"].notna() | finished.gt(0)
    )
    table = table[has_result].copy()

    table["risk_basis"] = table["experiment"].map(RISK_BASIS)
    table["risk_value"] = np.nan
    for experiment, basis in RISK_BASIS.items():
        mine = table["experiment"] == experiment
        table.loc[mine, "risk_value"] = table.loc[mine, basis]
    # Ties share a rank ("min"): two groups that both never kept burning are both e.g. 5th.
    table["risk_rank"] = (
        table.groupby("experiment")["risk_value"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )

    table["experiment"] = pd.Categorical(table["experiment"], EXPERIMENT_ORDER, ordered=True)
    table = table.sort_values(["experiment", "risk_rank", "material", "oxygen_pct"])
    table["experiment"] = table["experiment"].astype(str)

    rounded = {
        "spread_rate_mm_s_mean": 3,
        "burn_spread_mm_s_mean": 3,
        "risk_value": 3,
    }
    return table[RANKING_COLUMNS].round(rounded).reset_index(drop=True)


def main() -> None:
    ranking = build_ranking(pd.read_csv(MASTER), pd.read_csv(SAFFIRE2_CLEAN))
    ranking.to_csv(RANKING, index=False)
    print(f"ranking.csv: {len(ranking)} groups -> data/ranking.csv")
    for experiment, group in ranking.groupby("experiment", sort=False):
        top = group.head(5)[["material", "oxygen_pct", "tests", "risk_value", "risk_rank"]]
        print(f"\n{experiment} (ranked by {RISK_BASIS[experiment]}), top 5:")
        print(top.to_string(index=False))


if __name__ == "__main__":
    main()
