"""Day 8 (FIF-D08-DAT): clean the raw PSI tables into data/clean/*.csv.
Day 16 (FIF-D16-DAT): BASS-II (PSI-25) added as the 4th table, data/clean/bass2.csv.

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
BASS2_RAW = RAW / "PSI-25_Experimental table_BASS-II.csv"

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
                # Header says CO, but it is CO2 (Day 14 spot-check, data_notes.md section 10):
                # the headers drop every subscript ("O" = O2, "N" = N2) and the report names
                # CO2 as a tested suppressant.
                "co2_pct": raw["CO initial ambient composition; mole fraction"] * 100,
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


# --- BASS-II (PSI-25): ~130 solid-sample burns in a small flow duct on the ISS -----
#
# Most cells are notes typed during the test, not single values. In many tests the crew lit
# the sample and then lowered the airflow step by step until the flame went out, so the
# "Air display" cell is a list like "5  3  2  ext". Rules: data_notes.md section 13.

MM_PER_INCH = 25.4
MICRONS_PER_MM = 1000
# BASS-II flew in 2014 (and 3 tests in 2016). T9 and T18 say 6/24/2018, but their day-of-year
# (GMT 175) is 2014-06-24, so the year is a typo.
BASS2_YEAR_TYPOS = {2018: 2014}
# Final O2 can't drop to 0.6% or jump to 40% in a glovebox burn: those are sensor glitches.
BASS2_FINAL_O2_PCT = (5, 30)
# The report: "a small wind tunnel which could impose airflow speeds up to 40 cm/s".
BASS2_MAX_FLOW_CM_S = 40


def bass2_material(text: str) -> str:
    """One name per kind of sample, so charts can compare them. Raises on anything new.

    Films, slabs and clear rods are PMMA: the table names PMMA on most of them (B1, M1, O5
    "clear PMMA rod"). Black rods and spherical sections are never named, in the table or the
    report, so they keep a plain name instead of a guessed material (data_notes.md section 13)."""
    t = str(text).lower()
    if "sibal" in t:
        return "Cotton-Fiberglass (SIBAL)"  # Saffire-II's spelling
    if "nomex" in t:
        return "Nomex"
    if "candle" in t or "wax" in t:
        return "Japan wax candle"
    if "spher" in t:
        return "Spherical section"
    if "rod" in t or "blac" in t:
        return "Black rod" if "blac" in t else "PMMA rod"
    if "film" in t or "micron" in t:
        return "PMMA film"
    if "pmma" in t or "slab" in t:
        return "PMMA slab"
    raise ValueError(f"unknown BASS-II sample {text!r}: add a rule to bass2_material")


def bass2_thickness_mm(text: str) -> float:
    """Film or slab thickness, or rod diameter, in mm. '100 micron' -> 0.1, '0.2 mm' -> 0.2,
    '1/4" clear rod' -> 6.35, '0.5" black rod' -> 12.7. SIBAL, Nomex, the candle and the
    sphere give no thickness -> NaN."""
    t = str(text).lower()
    if "rod" in t or "blac" in t:
        fraction = re.search(r"(\d+)/(\d+)", t)
        if fraction:
            return round(int(fraction.group(1)) / int(fraction.group(2)) * MM_PER_INCH, 2)
        decimal = re.search(r"(\d*\.\d+)\s*\"", t)
        return round(float(decimal.group(1)) * MM_PER_INCH, 2) if decimal else float("nan")
    microns = re.search(r"(\d+(?:\.\d+)?)\s*micron", t)
    if microns:
        return float(microns.group(1)) / MICRONS_PER_MM
    mm = re.search(r"(\d+(?:\.\d+)?)\s*mm", t)
    return float(mm.group(1)) if mm else float("nan")


def bass2_width_cm(text: str) -> float:
    """Sample width: '2 cm wide' -> 2, '1 cm SIBAL' -> 1. Rods and the candle -> NaN."""
    t = str(text).lower()
    if "rod" in t or "candle" in t or "spher" in t:
        return float("nan")
    found = re.search(r"(\d+(?:\.\d+)?)\s*cm", t)
    return float(found.group(1)) if found else float("nan")


def _decimals(text: str) -> list[float]:
    """Like numbers_in, but '.5' is 0.5: BASS-II often drops the leading zero."""
    return [float(n) for n in re.findall(r"\d*\.\d+|\d+", text)]


def _bracketed(text: str) -> list[float]:
    return _decimals(" ".join(re.findall(r"\(([^)]*)\)", text)))


def bass2_flows(text) -> list[float]:
    """The air speeds (cm/s) written in an 'Air display' cell, in the order they were set.

    The cell also holds fan settings, which are not speeds: numbers in brackets, decimals
    marked 'pot' ('0.5 pot'), and everything after the word 'pot' ('pot 0.4', 'pots 0.4 0.36').
    The tunnel could blow at most 40 cm/s (report), so a bigger number is a fan reading, not
    a speed ('49  5 cm/s' -> 5). One test (O13a) has fan readings outside the brackets and the
    speeds inside: when nothing outside is a speed, the bracketed numbers are used."""
    if pd.isna(text):
        return []
    t = str(text).lower()
    outside = re.sub(r"\([^)]*\)", " ", t)
    outside = re.sub(r"\d*\.\d+\s*pot\b", " ", outside)  # '0.5 pot'
    outside = re.split(r"\bpots?\b", outside)[0]  # 'pot 0.4', 'pots 0.4 0.36 ...'
    speeds = [n for n in _decimals(outside) if n <= BASS2_MAX_FLOW_CM_S]
    if not speeds:
        speeds = [n for n in _bracketed(t) if n <= BASS2_MAX_FLOW_CM_S]
    return speeds


def bass2_lowest_flow_unknown(text) -> bool:
    """True when the cell says the air went lower than the speeds show: 'down to ext', '<1',
    'decr', 'low', or fan settings written after the speeds ('5 pots 0.4 0.36 off', or pot
    values in brackets like '5 2.5 (1.15 .5 .35)'). Also true when the air was raised from a
    start that isn't written ('incr to 28')."""
    t = "" if pd.isna(text) else str(text).lower()
    if re.search(r"down to|decr|low|<|\bpots?\b", t):
        return True
    bracketed = _bracketed(t)
    if bracketed and max(bracketed) < 2 and bass2_flows(text):
        return True  # pot settings below the lowest speed shown
    return "incr" in t and len(bass2_flows(text)) < 2


def bass2_outcome(fan, air) -> str | None:
    """How the flame ended, from the words typed in the fan and air cells.

    'no ign' -> No ignition; 'blowoff' (blown out by too much air) -> Blowoff; 'ext',
    'extinguished', 'out', 'off' or 'would not stay lit' -> Extinction. Nothing said ->
    None (unknown): we don't assume the flame kept burning."""
    t = f"{'' if pd.isna(fan) else fan} {'' if pd.isna(air) else air}".lower()
    if "no ign" in t:
        return "No ignition"
    if "blowoff" in t or "blow off" in t:
        return "Blowoff"
    if re.search(r"ext|\bout\b|\boff\b|would not stay lit", t):
        return "Extinction"
    return None


def bass2_date(text: str) -> str:
    date = pd.to_datetime(text, format="%m/%d/%Y")
    date = date.replace(year=BASS2_YEAR_TYPOS.get(date.year, date.year))
    return date.strftime("%Y-%m-%d")


def clean_bass2(path: Path = BASS2_RAW) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str)
    raw.columns = [" ".join(c.split()) for c in raw.columns]  # headers have runs of spaces
    raw = raw[raw["Test #"].notna()].copy()

    air = raw["Air display"]
    flows = air.map(bass2_flows)
    unknown_low = air.map(bass2_lowest_flow_unknown)
    oxygen = pd.to_numeric(raw["Calibrated initial O2 % by vol"], errors="coerce")
    final_o2 = pd.to_numeric(raw["Calibrated final O2 % by vol"], errors="coerce")
    sample_text = raw["Fuel Sample Material"].map(lambda t: " ".join(str(t).split()))

    return (
        pd.DataFrame(
            {
                "experiment": "BASS-II",
                "test_id": raw["Test #"].str.strip(),
                "test_date": raw["Date"].map(bass2_date),
                "pi": raw["PI"].str.strip(),
                "sample_id": raw["Sample #"].str.strip(),
                "sample_text": sample_text,  # kept as typed, so every parse can be checked
                "material": sample_text.map(bass2_material),
                "thickness_mm": sample_text.map(bass2_thickness_mm),
                "width_cm": sample_text.map(bass2_width_cm),
                # Initial O2 is the level the test started at; final O2 is after burning.
                "oxygen_pct_min": oxygen,
                "oxygen_pct_max": oxygen,
                "oxygen_final_pct": final_o2.where(final_o2.between(*BASS2_FINAL_O2_PCT)),
                # Lowest and highest air speed written. Lowest is empty when the air was
                # turned down further than the numbers show.
                "flow_cm_s_min": [
                    float("nan") if low or not f else min(f)
                    for f, low in zip(flows, unknown_low, strict=True)
                ],
                "flow_cm_s_max": flows.map(lambda f: max(f) if f else float("nan")),
                "flow_notes": air.map(lambda t: "" if pd.isna(t) else " ".join(str(t).split())),
                "outcome": [
                    bass2_outcome(f, a) for f, a in zip(raw["Fan display"], air, strict=True)
                ],
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
        "bass2.csv": clean_bass2(),
    }
    for name, df in tables.items():
        df.to_csv(CLEAN / name, index=False)
        print(f"{name}: {len(df)} rows x {df.shape[1]} columns -> data/clean/{name}")


if __name__ == "__main__":
    main()
