"""Day 10 (FIF-D10-DAT): data quality checks for the clean tables and master.csv.

Range checks: every number sits between limits that make sense for these experiments.
The limits are wide enough for every real row, but tight enough to catch a unit slip
(a mole fraction not x100, atm or mmHg not turned into kPa, mm/s mixed up with cm/s).
Duplicate checks: each fuel (FLEX-2), sample (Saffire-II) and test (FLEX) appears once.

master.csv has no id column and does have identical rows: different FLEX tests run at the
same conditions, and 3 Saffire-II Silicone samples at the same conditions. Those are real,
separate tests, so duplicates are checked by id in the clean tables, not by whole row.

Print a report for the saved files (run from the repo root):
    uv run python -m flame_in_freefall.check_data
tests/test_data_quality.py runs the same checks in pytest.
"""

import sys

import pandas as pd

from flame_in_freefall.build_master import CLEAN, CLEAN_FILES, MASTER
from flame_in_freefall.clean_tables import FLEX_RAW

# Lowest and highest believable value per column (missing values are not checked).
LIMITS = {
    # %. Real: 12-34. A mole fraction left as-is (0.21) falls below 5.
    "oxygen_pct_min": (5, 50),
    "oxygen_pct_max": (5, 50),
    # kPa. Real: 50.7-309. Unconverted atm (0.5-3) or mmHg (530-761) falls outside.
    "pressure_kpa_min": (10, 500),
    "pressure_kpa_max": (10, 500),
    # cm/s. Real: 0 (FLEX), 0.1-5 (FLEX-2), 20 (Saffire-II). mm/s by mistake would be 200.
    "flow_cm_s_min": (0, 50),
    "flow_cm_s_max": (0, 50),
    "spread_rate_mm_s": (0, 20),  # real: 2.1-2.6, flames spread slowly in microgravity
    "nitrogen_pct": (0, 100),
    "co_pct": (0, 100),
    "helium_pct": (0, 100),
    "droplet_diameter_mm": (0.5, 10),  # real: 1.1-4.7
    "extinction_diameter_mm": (0, 10),  # real: 0-4.6
    "burn_time_s": (0, 1200),  # real: 0.3 s (FLEX) to 900 s (Saffire-II)
    "thickness_mm": (0, 20),  # real: 0.27-10
    "burn_length_cm": (0, 50),  # real: 0-29
}

ALLOWED = {
    "experiment": {"FLEX-2", "Saffire-II", "FLEX"},
    "outcome": {"Extinction", "Completion", "Disruption"},
}

# FLEX tests ran on the ISS; real dates are 2009-03-05 to 2011-12-08.
FLEX_DATES = ("2008-01-01", "2013-12-31")

# The column that names one row of each clean table: every value must appear once.
ID_COLUMNS = {"flex2.csv": "material", "saffire2.csv": "sample_id", "flex.csv": "test_id"}

# FLEX gas mix: O2 + N2 + CO + He should add up to about 100%. The raw mole fractions
# have 2 decimals, so real totals land between 98 and 101.
GAS_COLUMNS = ["oxygen_pct_min", "nitrogen_pct", "co_pct", "helium_pct"]
GAS_TOTAL_PCT = (97, 102)
# A flame cannot go out on a droplet bigger than the one it started with. Allow 0.05 mm
# for measurement noise: C13H102 went out at 3.34 mm on a 3.33 mm droplet.
EXTINCTION_SLACK_MM = 0.05

# FLEX tests that share a date and time with another test in the raw file.
# 193F001 is listed twice (the repeat is dropped in cleaning). C11M201 has the same date
# and time as C11H201, and 0 mmHg pressure: its date, time and pressure look copied by mistake.
KNOWN_SAME_TIME = {"193F001", "C11M201", "C11H201"}


def _flag(table: pd.DataFrame, bad: pd.Series, message) -> list[str]:
    """One line per bad row, e.g. 'FLEX C13H102: burn_time_s = -1.0, expected 0 to 1200'.
    Rows are named by test or sample id; without one (master.csv, FLEX-2) by material
    and row number (0 = first data row)."""
    id_col = next((c for c in ("test_id", "sample_id") if c in table), None)

    def name(i) -> str:
        if id_col:
            return str(table.at[i, id_col])
        return f"{table.at[i, 'material']} (row {i})"

    return [
        f"{table.at[i, 'experiment']} {name(i)}: {message(table.loc[i])}"
        for i in table.index[bad.fillna(False)]
    ]


def range_problems(table: pd.DataFrame) -> list[str]:
    """Numbers outside LIMITS, unknown words, a min above its max, dates outside FLEX_DATES."""
    problems = []
    for col, (lo, hi) in LIMITS.items():
        if col in table:
            bad = table[col].notna() & ~table[col].between(lo, hi)
            problems += _flag(table, bad, lambda r: f"{col} = {r[col]}, expected {lo} to {hi}")
    for col, allowed in ALLOWED.items():
        if col in table:
            bad = table[col].notna() & ~table[col].isin(allowed)
            problems += _flag(table, bad, lambda r: f"{col} = {r[col]!r}, not a known value")
    for base in ("oxygen_pct", "pressure_kpa", "flow_cm_s"):
        lo, hi = f"{base}_min", f"{base}_max"
        if lo in table:
            bad = table[lo] > table[hi]  # False when either side is missing
            problems += _flag(table, bad, lambda r: f"{lo} = {r[lo]} is above {hi} = {r[hi]}")
    if "test_date" in table:
        dates = pd.to_datetime(table["test_date"], errors="coerce")
        bad = ~dates.between(*FLEX_DATES)  # also True for a date that does not parse
        problems += _flag(table, bad, lambda r: f"test_date = {r['test_date']}, outside FLEX")
    return problems


def duplicate_problems(table: pd.DataFrame, id_col: str) -> list[str]:
    """Ids that appear more than once."""
    counts = table[id_col].value_counts()
    experiment = table["experiment"].iloc[0]
    return [f"{experiment} {i}: listed {n} times" for i, n in counts[counts > 1].items()]


def flex_consistency_problems(flex: pd.DataFrame) -> list[str]:
    """FLEX rows whose gas mix does not add up, or whose flame outgrew its droplet."""
    gas = flex[GAS_COLUMNS].sum(axis=1)
    lo, hi = GAS_TOTAL_PCT
    problems = _flag(flex, ~gas.between(lo, hi), lambda r: f"gas mix adds up to {gas[r.name]:.0f}%")
    grew = flex["extinction_diameter_mm"] > flex["droplet_diameter_mm"] + EXTINCTION_SLACK_MM
    return problems + _flag(
        flex,
        grew,
        lambda r: (
            f"extinction diameter {r['extinction_diameter_mm']} mm is bigger than "
            f"the {r['droplet_diameter_mm']} mm droplet"
        ),
    )


def same_time_tests(path=FLEX_RAW) -> set[str]:
    """FLEX ids that share their date and time with another test in the raw file."""
    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]
    same = raw.duplicated(subset=["Test Date", "Test GMT"], keep=False)
    return set(raw.loc[same, "FLEX Identifier"])


def check_all(tables: dict[str, pd.DataFrame], master: pd.DataFrame) -> list[str]:
    """Every check on the three clean tables (keyed by file name) and master.csv."""
    problems = []
    for name, table in tables.items():
        problems += range_problems(table) + duplicate_problems(table, ID_COLUMNS[name])
    problems += flex_consistency_problems(tables["flex.csv"])
    problems += range_problems(master)
    new = same_time_tests() - KNOWN_SAME_TIME
    return problems + [f"FLEX {i}: shares its date and time with another test" for i in new]


def main() -> None:
    tables = {name: pd.read_csv(CLEAN / name) for name in CLEAN_FILES}
    master = pd.read_csv(MASTER)
    problems = check_all(tables, master)
    rows = sum(len(t) for t in tables.values())
    print(f"Checked {rows} clean rows in data/clean/ and {len(master)} rows in data/master.csv.")
    if not problems:
        print("No problems found.")
        return
    print(f"{len(problems)} problem(s):")
    print("\n".join(f"- {p}" for p in problems))
    sys.exit(1)


if __name__ == "__main__":
    main()
