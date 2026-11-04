# Data notes: locked scope (Day 7, FIF-D07-DAT)

Question (see `docs/the_question.md`): *At what oxygen levels and airflow speed does a fire in space keep burning or go out, for different materials?*

## 1. Final experiments

| Experiment | PSI id | Raw file | Role in `master.csv` |
|---|---|---|---|
| FLEX | PSI-69 | `data/raw/PSI-69_Experimental table_FLEX.csv` | **Main source.** 274 per-test rows with fuel, oxygen, pressure and outcome. |
| Saffire-II | PSI-99 | `data/raw/PSI-99_Experimental table_SAFFIRE-2.csv` | **Second source.** 9 real samples: material, ~O2, airflow (20 cm/s), spread rate. |
| FLEX-2 | PSI-68 | `data/raw/PSI-68_Experimental table_Flex2.csv` | **Reference only.** 8 rows of planned ranges, no outcome, so it is not merged into `master.csv`. Used to show the tested oxygen and airflow ranges. |

BASS was in the original plan but we never downloaded it; it is **out of scope**. (Fallback rule from the sprint plan: if scope slips, stay at these 2 merged experiments.)

Reports in `data/reports/` and their links in `data/sources.csv` are the text side (for search).

## 2. Final columns of `master.csv`

One row = one test (FLEX) or one sample (Saffire-II).

| Column | Unit | FLEX source | Saffire-II source |
|---|---|---|---|
| experiment | n/a | constant `FLEX` | constant `Saffire-II` |
| material | n/a | `Fuel` | `Material` (blank cells filled from the row above) |
| oxygen_pct | % | `O initial ambient composition; mole fraction` x 100 | `Percent O2 (Note 1)`, take the first number, approximate |
| pressure_kpa | kPa | `Ambient pressure; mmHg` x 0.13332 (0 treated as missing) | not in table (ambient cabin, leave empty) |
| flow_cm_s | cm/s | none (0, no airflow in droplet tests) | `Air Flow (cm/s)` |
| spread_rate_mm_s | mm/s | none (droplet, no spread); burning rate stays out | `?-g Spread Length` (it is really a rate, `n/a` becomes missing) |
| outcome | n/a | `Test end`: Extinction = went out, Completion = burned; Disruption rows dropped | derived: `~ 0` burn length = went out, otherwise burned |

`outcome` is **new compared to contract v1.0**. The question needs it, so the contract must get it in a small PR (BE owns the contract). The contract also names `BASS`; it should say FLEX / Saffire-II.

## 3. Decisions and open assumptions

- Dropped: FLEX `Disruption` tests (61), Saffire-II footnote and flow-visualization rows, camera columns, FLEX identifiers and dates (not needed for the question).
- To confirm in the reports on Day 8-10: FLEX `CO` column really is CO2; FLEX `Burning rate; mm` is really mm^2/s; Saffire `?-g Spread Length` is a rate; the exact meaning of `Disruption`.
- Known thin spot: airflow only exists in Saffire-II (one value) and as FLEX-2 ranges. The answer for airflow will lean on those, and the app should say so.
- Cleaning (Day 8) writes `data/processed/` CSVs, Day 9 builds `master.csv` from them.
