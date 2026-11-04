# Data notes: locked scope (Day 7, FIF-D07-DAT)

Question (see `docs/the_question.md`): *At what oxygen levels and airflow speed does a fire in space keep burning or go out, for different materials?*

## 1. Final experiments

Order of priority: FLEX-2, Saffire-II, FLEX.

| Experiment | PSI id | Raw file | Role in `master.csv` |
|---|---|---|---|
| FLEX-2 | PSI-68 | `data/raw/PSI-68_Experimental table_Flex2.csv` | **Main source.** 8 rows (one per fuel) with oxygen levels, airflow range, pressure and ambient gas. Values are ranges/lists, so they are parsed into min/max or exploded to one row per value. No outcome column. |
| Saffire-II | PSI-99 | `data/raw/PSI-99_Experimental table_SAFFIRE-2.csv` | **Second source.** 9 real samples: material, ~O2, airflow (20 cm/s), spread rate and a derivable outcome. |
| FLEX | PSI-69 | `data/raw/PSI-69_Experimental table_FLEX.csv` | **Supporting source.** 274 per-test rows (methanol, heptane) with oxygen, pressure and outcome. Fills the outcome gap of FLEX-2 for the same fuels, but has no airflow. |

BASS was in the original plan but we never downloaded it; it is **out of scope**. (Fallback rule from the sprint plan: if scope slips, stay at these experiments.)

Reports in `data/reports/` and their links in `data/sources.csv` are the text side (for search).

## 2. Final columns of `master.csv`

One row = one test condition (FLEX-2 value combination), one sample (Saffire-II) or one test (FLEX).

| Column | Unit | FLEX-2 source | Saffire-II source | FLEX source |
|---|---|---|---|---|
| experiment | n/a | constant `FLEX-2` | constant `Saffire-II` | constant `FLEX` |
| material | n/a | `Sample (Fuel Type)` | `Material` (blank cells filled from the row above) | `Fuel` |
| oxygen_pct | % | `Oxygen Mole Fraction` list x 100 | `Percent O2 (Note 1)`, first number, approximate | `O initial ambient composition; mole fraction` x 100 |
| pressure_kpa | kPa | `Ambient Pressure (atm)` x 101.325 | not in table (leave empty) | `Ambient pressure; mmHg` x 0.13332 (0 treated as missing) |
| flow_cm_s | cm/s | `Flow Velocity (cm/s)` range (min and max) | `Air Flow (cm/s)` | none (0, no airflow in droplet tests) |
| spread_rate_mm_s | mm/s | none | `?-g Spread Length` (really a rate, `n/a` becomes missing) | none (droplet, no spread) |
| outcome | n/a | none (empty) | derived: `~ 0` burn length = went out, otherwise burned | `Test end`: Extinction = went out, Completion = burned; Disruption rows dropped |

`outcome` is **new compared to contract v1.0**. The question needs it, so the contract must get it in a small PR (BE owns the contract). The contract also names `BASS`; it should say FLEX-2 / Saffire-II / FLEX.

## 3. Decisions and open assumptions

- Dropped: FLEX `Disruption` tests (61), Saffire-II footnote and flow-visualization rows, camera columns, FLEX identifiers and dates (not needed for the question). FLEX-2 droplet diameter and temperature are not kept.
- To confirm in the reports on Day 8-10: FLEX `CO` column really is CO2; FLEX `Burning rate; mm` is really mm^2/s; Saffire `?-g Spread Length` is a rate; the exact meaning of `Disruption`.
- Known thin spot: FLEX-2 is the main source but has no outcome, and its values are planned ranges, not measurements. Outcome comes only from Saffire-II and FLEX, and airflow only from FLEX-2 and Saffire-II (one value). The app should say so.
- Cleaning (Day 8) writes `data/processed/` CSVs, Day 9 builds `master.csv` from them.
