"""Day 8 (FIF-D08-DAT): clean the three raw PSI tables into data/clean/*.csv.

Rules come from data_notes.md (scope) and docs/column_dictionary.md (messy values).
Run from the repo root:  uv run python -m flame_in_freefall.clean_tables
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"

FLEX2_RAW = RAW / "PSI-68_Experimental table_Flex2.csv"
SAFFIRE2_RAW = RAW / "PSI-99_Experimental table_SAFFIRE-2.csv"
FLEX_RAW = RAW / "PSI-69_Experimental table_FLEX.csv"

ATM_TO_KPA = 101.325
MMHG_TO_KPA = 0.133322

NUMBER = re.compile(r"\d+(?:\.\d+)?")
# References like 'Note 4' or 'See Fig. 5' contain a digit that is not a measurement.
REFERENCE = re.compile(r"(note|fig\.?)\s*\d+", re.IGNORECASE)


def numbers_in(text) -> list[float]:
    """All numbers in a messy text cell: '0.17; 0.21;0.25' -> [0.17, 0.21, 0.25].
    Note/figure references are ignored: 'Note 4' -> [], '~ 10 cm (note 3)' -> [10.0]."""
    if pd.isna(text):
        return []
    return [float(n) for n in NUMBER.findall(REFERENCE.sub("", str(text)))]


def first_number(text) -> float:
    """First number in a cell ('20 cm/s' -> 20.0, '~ 21.5' -> 21.5), NaN if there is none
    ('n/a', 'Note 4', 'Insignificant', '�')."""
    found = numbers_in(text)
    return found[0] if found else float("nan")


def tidy_material(name: str) -> str:
    """One spelling across tables: drop the '(pure)' / '(mixture)' labels.
    'Heptane (pure)' -> 'Heptane', so it matches FLEX's 'Heptane'."""
    name = re.sub(r"\s*\((pure|mixture)\)\s*", " ", str(name))
    return " ".join(name.split())


# --- FLEX-2 (PSI-68): planned test matrix, one row per fuel -------------------------


def clean_flex2(path: Path = FLEX2_RAW) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]  # headers have stray spaces

    oxygen = raw["Oxygen Mole Fraction"].map(numbers_in)  # mole fraction list
    pressure = raw["Ambient Pressure (atm)"].map(numbers_in)  # atm list
    flow = raw["Flow Velocity (cm/s)"].map(numbers_in)  # '0.1 - 5' range

    return pd.DataFrame(
        {
            "experiment": "FLEX-2",
            "material": raw["Sample (Fuel Type)"].map(tidy_material),
            "gas_mixture": raw["Ambient Gas Mixture"].str.strip(),
            "oxygen_pct_min": oxygen.map(min) * 100,
            "oxygen_pct_max": oxygen.map(max) * 100,
            "pressure_kpa_min": pressure.map(min) * ATM_TO_KPA,
            "pressure_kpa_max": pressure.map(max) * ATM_TO_KPA,
            "flow_cm_s_min": flow.map(min),
            "flow_cm_s_max": flow.map(max),
        }
    ).round(3)


# --- Saffire-II (PSI-99): 9 burned samples on the ISS ------------------------------


def thickness_mm(text) -> float:
    """'0.27 mm' -> 0.27, '1 cm' -> 10, '037 mm' -> 0.37 (typo in the raw file).
    'See Fig. 5' and the two-material '0.85 and 0.37 mm' have no single value -> NaN."""
    text = str(text).strip()
    if text == "037 mm":
        return 0.37
    if "and" in text or not numbers_in(text):
        return float("nan")
    value = first_number(text)
    return value * 10 if text.endswith("cm") else value


def clean_saffire2(path: Path = SAFFIRE2_RAW) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]
    # Real samples are 2-1 .. 2-9; the rest are flow-visualization rows and footnotes.
    raw = raw[raw["Sample Number"].str.match(r"^2-\d$", na=False)].copy()

    # Blank material = same material as the sample above (2-6 is SIBAL, 2-9 is PMMA).
    material = raw["Material"].ffill()
    oxygen = raw["Percent O2 (Note 1)"].map(numbers_in)  # '~ 22.1' or '22.1 to 22.0'
    flow = raw["Air Flow (cm/s)"].map(first_number)  # '20 cm/s'

    return pd.DataFrame(
        {
            "experiment": "Saffire-II",
            "sample_id": raw["Sample Number"],
            "material": material,
            "thickness_mm": raw["Samle Thickness"].map(thickness_mm),
            "flow_direction": raw["Flow Direction"].str.lower(),
            "oxygen_pct_min": oxygen.map(min),
            "oxygen_pct_max": oxygen.map(max),
            "flow_cm_s_min": flow,
            "flow_cm_s_max": flow,
            # Header is mojibake for 'micro-g'; the column holds a rate in mm/s.
            # 'n/a', 'n/a (Nomex)' and 'Note 4' (flame anchored, did not spread) -> NaN.
            "spread_rate_mm_s": raw["?-g Spread Length"].map(first_number),
            # '~ 0' -> 0, '29 cm' -> 29, '5 cm & 0 (note 2)' -> 5 (the PMMA part).
            "burn_length_cm": raw["?-g Burn Length"].map(first_number),
            "burn_time_s": raw["Burn Time (s)"].map(first_number),  # 'Insignificant' -> NaN
        }
    ).reset_index(drop=True)


# --- FLEX (PSI-69): 274 droplet tests --------------------------------------------


def clean_flex(path: Path = FLEX_RAW) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]

    # 193F001 is listed twice (tests #70 and #73) with the same date, time and
    # conditions: keep the first, drop the repeat.
    raw = raw.drop_duplicates(subset="FLEX Identifier", keep="first")

    # 0 mmHg (test C11M201) is impossible -> missing.
    pressure_kpa = raw["Ambient pressure; mmHg"].replace(0, float("nan")) * MMHG_TO_KPA
    oxygen_pct = raw["O initial ambient composition; mole fraction"] * 100

    return (
        pd.DataFrame(
            {
                "experiment": "FLEX",
                "test_id": raw["FLEX Identifier"],
                # Mixed 2- and 4-digit years ('10/24/09', '3/5/2009') -> ISO dates.
                "test_date": pd.to_datetime(raw["Test Date"], format="mixed").dt.strftime(
                    "%Y-%m-%d"
                ),
                "material": raw["Fuel"].map(tidy_material),
                "oxygen_pct_min": oxygen_pct,
                "oxygen_pct_max": oxygen_pct,
                "pressure_kpa_min": pressure_kpa,
                "pressure_kpa_max": pressure_kpa,
                "flow_cm_s_min": 0.0,  # droplet tests in still gas: no airflow
                "flow_cm_s_max": 0.0,
                "nitrogen_pct": raw["N initial ambient composition; mole fraction"] * 100,
                # Header says CO; likely CO2 (unconfirmed, see data_notes.md), name kept as-is.
                "co_pct": raw["CO initial ambient composition; mole fraction"] * 100,
                "helium_pct": raw["He initial ambient composition; mole fraction"] * 100,
                # '�' (corrupted "no value") -> NaN; '~6' -> 6.
                "droplet_diameter_mm": raw["Droplet initial diameter; mm"].map(first_number),
                "extinction_diameter_mm": raw["Visible flame extinction diameter; mm"].map(
                    first_number
                ),
                "burn_time_s": raw["Burn time; s"].map(first_number),
                "outcome": raw["Test end"].str.strip(),  # Extinction / Completion / Disruption
            }
        )
        .round(3)
        .reset_index(drop=True)
    )


def main() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)
    tables = {
        "flex2.csv": clean_flex2(),
        "saffire2.csv": clean_saffire2(),
        "flex.csv": clean_flex(),
    }
    for name, df in tables.items():
        df.to_csv(CLEAN / name, index=False)
        print(f"{name}: {len(df)} rows x {df.shape[1]} columns -> data/clean/{name}")


if __name__ == "__main__":
    main()
