# Data notes: locked scope (Day 7, FIF-D07-DAT)

Question (see `docs/the_question.md`): *At what oxygen levels and airflow speed does a fire in space keep burning or go out, for different materials?*


## 1. Final experiments

Order of priority: FLEX-2, Saffire-II, FLEX.

| Experiment | PSI id | Raw file | Role in `master.csv` |
|---|---|---|---|
| FLEX-2 | PSI-68 | `data/raw/PSI-68_Experimental table_Flex2.csv` | **Main source.** 8 rows (one per fuel) with oxygen levels, airflow range, pressure and ambient gas. Values are ranges/lists, so each one is parsed into a min and a max column (one row per fuel). No outcome column. |
| Saffire-II | PSI-99 | `data/raw/PSI-99_Experimental table_SAFFIRE-2.csv` | **Second source.** 9 real samples: material, ~O2, airflow (20 cm/s), spread rate. No outcome column. |
| FLEX | PSI-69 | `data/raw/PSI-69_Experimental table_FLEX.csv` | **Supporting source.** 274 per-test rows (methanol, heptane) with fuel, oxygen and pressure, but no airflow. The only table with an outcome: `Test end`. |

What each raw table has (checked against the files in `data/raw/`):

| Variable | FLEX-2 | Saffire-II | FLEX |
|---|---|---|---|
| Material / fuel | yes: `Sample (Fuel Type)` | yes: `Material` | yes: `Fuel` |
| Oxygen level | yes: `Oxygen Mole Fraction` | yes: `Percent O2 (Note 1)` | yes: `O initial ambient composition; mole fraction` |
| Airflow | yes: `Flow Velocity (cm/s)` | yes: `Air Flow (cm/s)` | no |
| Ambient gas mixture | yes: `Ambient Gas Mixture` | no | partly (separate N, CO, He fractions) |
| Outcome | no | no | yes: `Test end` (Extinction 186, Disruption 61, Completion 27) |

Note: `data/downloads.csv` still says `has_material = no` for FLEX-2 and Saffire-II, which does not match the files. It should be corrected to `yes`.

BASS was in the original plan but we never downloaded it; it is **out of scope**. (Fallback rule from the sprint plan: if scope slips, stay at these experiments.)

Reports in `data/reports/` and their links in `data/sources.csv` are the text side (for search).

## 2. Final columns of `master.csv`

One row = one fuel (FLEX-2, 8 rows), one sample (Saffire-II, 9 rows) or one test (FLEX, 274 rows).

Oxygen, pressure and airflow are stored as **min and max columns**. FLEX-2 gives ranges/lists, so min and max differ. When a source has a single value, the same number goes in both min and max.

| Column | Unit | FLEX-2 source | Saffire-II source | FLEX source |
|---|---|---|---|---|
| experiment | n/a | constant `FLEX-2` | constant `Saffire-II` | constant `FLEX` |
| material | n/a | `Sample (Fuel Type)` | `Material` (blank cells filled from the row above) | `Fuel` |
| oxygen_pct_min | % | lowest value in `Oxygen Mole Fraction` list x 100 (17) | `Percent O2 (Note 1)`, lowest number (`~` removed, approximate) | `O initial ambient composition; mole fraction` x 100 |
| oxygen_pct_max | % | highest value in `Oxygen Mole Fraction` list x 100 (30) | `Percent O2 (Note 1)`, highest number (same as min unless written as `22.1 to 22.0`) | same as min |
| pressure_kpa_min | kPa | lowest value in `Ambient Pressure (atm)` list x 101.325 (0.5 atm) | not in table (leave empty) | `Ambient pressure; mmHg` x 0.13332 (0 treated as missing) |
| pressure_kpa_max | kPa | highest value in `Ambient Pressure (atm)` list x 101.325 (3.0 atm) | not in table (leave empty) | same as min |
| flow_cm_s_min | cm/s | lower end of `Flow Velocity (cm/s)` range (0.1) | `Air Flow (cm/s)` (20) | 0 (no airflow in droplet tests) |
| flow_cm_s_max | cm/s | upper end of `Flow Velocity (cm/s)` range (5) | `Air Flow (cm/s)` (20) | 0 |
| spread_rate_mm_s | mm/s | none | `?-g Spread Length` (really a rate, `n/a` becomes missing) | none (droplet, no spread) |
| outcome | n/a | none (empty) | none (empty) | `Test end`, kept as-is: `Extinction` (flame went out), `Completion` (fuel burned away), `Disruption` (test cut short). All 3 values kept, including `Disruption`. |

**Changes compared to contract v1.0** (BE owns the contract, so these need a small PR there):
- `oxygen_pct`, `pressure_kpa` and `flow_cm_s` are each split into `_min` and `_max` columns. The `oxygen_min` / `oxygen_max` filters in `get_table()` must be pointed at these columns.
- `outcome` is new and is filled only for FLEX rows.
- The contract names `BASS`; it should say FLEX-2 / Saffire-II / FLEX.
- Some cells are empty (for example Saffire-II pressure, FLEX spread rate). `get_table()` currently runs `float()` on every number and would crash on them, so it must allow empty values.

## 3. Decisions and open assumptions

- Dropped: FLEX burning-rate column, Saffire-II footnote and flow-visualization rows, camera columns, FLEX identifiers and dates (not needed for the question). FLEX-2 droplet diameter and temperature are not kept.
- To confirm in the reports on Day 8-10: FLEX `CO` column really is CO2; FLEX `Burning rate; mm` is really mm^2/s; Saffire `?-g Spread Length` is a rate; the exact meaning of FLEX `Disruption`.
- FLEX `Disruption` tests (61) are **kept** in `master.csv`. Charts or summaries about "burned vs went out" can filter them out using `outcome`.
- Known thin spot: only FLEX has an outcome (`Test end`), and FLEX has no airflow. FLEX-2 (the main source) holds planned ranges, not measurements. Airflow only comes from FLEX-2 and Saffire-II (one value). The app should say so.
- Messy values to fix during Day 8 cleaning are listed per table in `docs/column_dictionary.md`. Examples: `�` and `~6` in FLEX numeric columns, the duplicate FLEX ID `193F001`, the zero pressure in `C11M201`, mixed date formats, and in Saffire-II, units inside values (`20 cm/s`), words mixed with numbers (`~ 0`, `Note 4`, `n/a (Nomex)`) and the `037 mm` typo. Material names also need one spelling across tables (FLEX-2 `Heptane (pure)` vs FLEX `Heptane`).
- Cleaning (Day 8) writes cleaned CSVs to `data/clean/` (`flex2.csv`, `saffire2.csv`, `flex.csv`), and Day 9 builds `master.csv` from them. Rebuild with `uv run python -m flame_in_freefall.clean_tables`.

## 4. Cleaning decisions (Day 8, FIF-D08-DAT)

- Every column renamed to snake_case with the unit in the name (`oxygen_pct_min`, `pressure_kpa_max`, `burn_time_s`).
- Units: mole fraction x 100 = %, atm x 101.325 = kPa, mmHg x 0.133322 = kPa, Saffire thickness in cm x 10 = mm.
- Placeholders become empty (missing): `�`, `n/a`, `n/a (Nomex)`, `Note 4`, `Insignificant`, `See Fig. 5`. Approximate values keep their number: `~6` = 6, `~ 0` = 0.
- FLEX `193F001` appears twice (tests #70 and #73) with the same date, time and conditions; the first is kept, so FLEX has 273 rows.
- FLEX `C11M201` pressure of 0 mmHg becomes missing.
- FLEX dates are written as `YYYY-MM-DD`; FLEX `Test GMT` is dropped.
- Material spelling: `(pure)` and `(mixture)` are removed, so FLEX-2 `Heptane (pure)` matches FLEX `Heptane`.
- Saffire-II: blank materials filled from the row above; `037 mm` read as 0.37 mm; `0.85 and 0.37 mm` (PMMA & Nomex, two thicknesses) left empty; burn length `5 cm & 0 (note 2)` read as 5 cm (the PMMA part).
- Extra columns kept in the clean tables (not all go into `master.csv`): FLEX-2 `gas_mixture`; Saffire-II `sample_id`, `thickness_mm`, `flow_direction`, `burn_length_cm`, `burn_time_s`; FLEX `test_id`, `test_date`, `nitrogen_pct`, `co_pct`, `helium_pct`, droplet and extinction diameters, `burn_time_s`.
