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

Reports in `docs/reports/` and their links in `data/sources.csv` are the text side (for search).

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
- To confirm in the reports on Day 8-10: FLEX `CO` column really is CO2 (**confirmed on Day 14**, section 10); FLEX `Burning rate; mm` is really mm^2/s; Saffire `?-g Spread Length` is a rate; the exact meaning of FLEX `Disruption`.
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
- Extra columns kept in the clean tables (not all go into `master.csv`): FLEX-2 `gas_mixture`; Saffire-II `sample_id`, `thickness_mm`, `flow_direction`, `burn_length_cm`, `burn_time_s`; FLEX `test_id`, `test_date`, `nitrogen_pct`, `co2_pct` (called `co_pct` until Day 14), `helium_pct`, droplet and extinction diameters, `burn_time_s`.

## 5. Building `master.csv` (Day 9, FIF-D09-DAT)

- Saved at `data/master.csv`: 290 rows (FLEX-2 8, Saffire-II 9, FLEX 273) with the 10 columns in section 2, in that order.
- Rebuild from scratch: `uv run python -m flame_in_freefall.clean_tables` then `uv run python -m flame_in_freefall.build_master`.
- The master table only stacks the clean tables and keeps the section 2 columns; no values are changed. A column a source lacks is left empty.
- `tests/test_master.py` checks the columns, the row counts and the expected empty cells. It also checks that the saved `data/master.csv` matches a fresh build, so re-run both commands after any cleaning change.

## 6. Data quality checks (Day 10, FIF-D10-DAT)

- Checks live in `src/flame_in_freefall/check_data.py`; `tests/test_data_quality.py` runs them in pytest (so CI runs them too).
- Print a report for the saved files: `uv run python -m flame_in_freefall.check_data` (prints "No problems found", or one line per problem and exits with an error).
- **Range checks:** each number must sit between limits that fit these experiments (listed with the real min/max in `LIMITS`). They are set to catch unit slips: a mole fraction not x100, atm or mmHg not turned into kPa, mm/s instead of cm/s. Also checked: every `_min` is at most its `_max`, `experiment` and `outcome` only use known words, FLEX dates fall in the mission years, the FLEX gas mix (O2 + N2 + CO2 + He) adds up to 97-102%, and no flame went out on a droplet bigger than the starting one.
- **Duplicate checks:** each FLEX-2 fuel, Saffire-II `sample_id` and FLEX `test_id` appears once.
- `master.csv` **does** have 10 rows that are exact copies of other rows. They are not mistakes: different FLEX tests run at the same conditions, and 3 Saffire-II Silicone samples at the same conditions. Don't drop them; charts that count tests should count them.
- The tests also plant mistakes (for example 760 in a kPa column, a repeated test id) and check they are caught.

Found while checking (left as-is, to confirm in the reports):
- FLEX `C11M201` has the same date and time as `C11H201` (2010-09-06 19:14:22), while the other C11M tests ran on 2010-09-01. Together with its 0 mmHg pressure, its date, time and pressure look copied by mistake. Its oxygen and gas mix match the other C11M tests, so the row is kept.
- FLEX `193F001`'s two copies differ slightly in droplet diameter (4.67 vs 4.64 mm) and extinction diameter (4.60 vs 4.58 mm), so it may have been run twice, not entered twice. The first copy is still the one kept (section 4).
- FLEX `C13H102`: the flame went out at 3.34 mm on a 3.33 mm droplet. Treated as measurement noise (0.05 mm allowed).

## 7. Helpful columns (Day 11, FIF-D11-DAT)

- `master.csv` now has **12 columns**: `material_category` is inserted after `material`, and `spread_rate_per_flow` after `spread_rate_mm_s`. Rows are unchanged (290).
- `material_category`: one of `hydrocarbon`, `alcohol` (liquid fuels), `plastic`, `fabric`, `silicone`, `plastic + fabric` (Saffire-II solids). Filled on every row.
- `spread_rate_per_flow` is the normalized spread rate: the spread rate divided by the airflow speed, both in mm/s, so it has no unit. It is filled only for the 2 SIBAL samples (0.0105 and 0.013), because only they have a spread rate.
- Full definitions, the material-to-category table and the reasons are in `docs/column_dictionary.md` section 4.
- Quality checks (section 6) now also check these columns. `material_category` must be a known category, and `spread_rate_per_flow` must be between 0 and 0.1. An airflow left in cm/s would give about 0.1-0.13, so the check catches it.
- **For BE (contract):** these are two more columns on top of the section 2 changes. `get_table()` and `master.mock.csv` don't have them yet. `material_category` would also be a useful filter, so charts can be coloured or filtered by category.

## 8. Chunks tagged by experiment (Day 12, FIF-D12-DAT)

- Each report is linked to its experiment in the `experiment` column of `data/sources.csv`: `flex_abstract.txt` is FLEX, `flex2_abstract.txt` is FLEX-2, and `saffire2_abstract.txt` is Saffire-II. BASS has no report and is out of scope (section 1).
- `chunk_reports()` in `src/flame_in_freefall/chunking.py` copies that value onto every chunk. Each line of `data/processed/chunks.jsonl` now has 5 fields: `id`, `text`, `source`, `page`, `experiment`. There are 18 chunks: FLEX 7, FLEX-2 7, Saffire-II 4.
- The names are spelled exactly as in the `experiment` column of `master.csv`, so one dropdown value (for example `Saffire-II`) can filter both search and the table.
- A report with no experiment in `sources.csv` (a missing column or a blank cell) stops the chunking with an error. An untagged chunk would never appear in a filtered search, so it fails loudly instead.
- Rebuild: run `uv run python scripts/day7_chunk_reports.py`, then `uv run python scripts/day8_embed_chunks.py`. The search index is built from `chunks.jsonl`, so the second command is what makes `experiment` show up in search results.
- `tests/test_chunking.py` checks that every chunk has the right experiment, that the names match `master.csv`, and that an untagged report fails.
- **For AI (D12-AI):** the tag is in the chunk metadata saved with the index. Filter on `chunk["experiment"]` before ranking.
- **For BE (D12-BE, contract v1.1):** contract section 2 should list `experiment` (str, `FLEX-2` / `Saffire-II` / `FLEX`) as a chunk field. `search()` results will then include it too. `data/mock/chunks.mock.jsonl` doesn't have the field yet and still uses BASS names. Its test (`tests/test_mock_data.py`) needs the field added when the mock gets it.

## 9. Riskiness ranking table (Day 13, FIF-D13-DAT)

- Saved at `data/ranking.csv`: one row per experiment + material + oxygen level, with spread-rate stats, outcome counts and a rank (1 = riskiest). 30 rows: Saffire-II 4, FLEX 26. Columns are in `docs/column_dictionary.md` section 5.
- Rebuild (after `build_master`): `uv run python -m flame_in_freefall.build_ranking`. It prints the top 5 of each experiment.
- **Grouping by oxygen:** each row's oxygen is the middle of its min and max, rounded to a whole percent (0.5 rounds up). FLEX tests sit at whole percents already. Saffire-II's 21.5-22.1% all become 22%. The report calls those values approximate, so they count as one level.
- **Pressure is not a group key** (the ticket asks for material and oxygen). FLEX groups mix tests at about 50, 70 and 100 kPa, so a group's result can hide a pressure effect.

**Why the spread-rate stats alone weren't enough:** `master.csv` has a measured spread rate for only 2 rows (the SIBAL samples, 2.1 and 2.6 mm/s). They are kept as `spread_rate_mm_s_min/mean/max`, but a ranking built only on them would hold one material. So each experiment is ranked on the best measure it has:

| Experiment | Ranked by | Riskiest | Least risky |
|---|---|---|---|
| Saffire-II (solid sheets) | `burn_spread_mm_s_mean` = burn length / burn time, in mm/s | SIBAL 2.26 mm/s | Silicone 0 (never spread) |
| FLEX (fuel droplets) | `kept_burning_share` = completion / (completion + extinction) | Heptane 30% and Methanol 34% (1.0) | 12 groups at 0, mostly Methanol at 12-20% |

- **Burn length / burn time** comes from `data/clean/saffire2.csv` (master leaves those columns out), joined on experiment + material + oxygen level. For SIBAL, which also has a measured rate, it gives 2.0 and 2.5 mm/s against a measured 2.1 and 2.6, so it is a fair stand-in. A test checks they agree within 0.15 mm/s. Silicone burned 0 cm with an "Insignificant" burn time, so its spread is 0, not empty. Saffire-II order: SIBAL 2.26 > PMMA & Nomex 0.36 > PMMA 0.14 > Silicone 0.
- **Kept-burning share** counts only tests that finished. `Disruption` (test cut short) is left out, because we don't know if that flame would have gone out. Three FLEX groups have only disruptions (Heptane 25% and 34%, Methanol 25%: 10 tests). They have nothing to rank on, so they are not in the table.
- **FLEX-2 is not in the table**: its 8 rows are planned ranges with no spread rate and no outcome.
- **Ranks are within one experiment only.** A spread speed in mm/s and a share of tests can't go on one scale, so Saffire-II rank 1 and FLEX rank 1 mean different things. `risk_value` holds the number behind the rank so one chart column works for both, but it needs one panel or colour per experiment.

What the table shows (for the question in `docs/the_question.md`):
- FLEX: more oxygen means more flames keep burning. Below 17% no Methanol flame and only 3 of 14 finished Heptane tests kept burning. At 30% and above, 4 of 6 finished tests kept burning. Heptane keeps burning more often than Methanol at the same oxygen (for example at 18%: 4 of 16 vs 1 of 19).
- Saffire-II: at about 22% oxygen and 20 cm/s airflow, the cotton-fiberglass fabric (SIBAL) spread about 6x faster than PMMA with Nomex and 16x faster than PMMA. Silicone did not spread.

Caveats (the app should show them next to the chart):
- Small groups. Heptane 30% ranks 1st on 1 finished test (6 were disruptions). Every group's `tests`, `completion`, `extinction` and `disruption` are in the table, so the chart can show them on hover.
- Saffire-II is 9 samples at one oxygen level (about 22%) and one airflow, so it ranks materials but says nothing about oxygen.
- Burn time may include the time to ignite, which would make `burn_spread_mm_s_mean` a little low. For SIBAL it is only 0.1 mm/s below the measured rate.

Tests: `tests/test_ranking.py` checks the columns, one row per group, the oxygen rounding, the burn-spread estimate against the measured rate, the Saffire-II order, the share leaving out disruptions, ties sharing a rank, and that the saved `data/ranking.csv` matches a fresh build. Re-run `build_ranking` after any change to cleaning or `master.csv`.

- **For FE (D13-FE, ranking chart from real data):** read `data/ranking.csv`. Plot `risk_value` by material with one panel (or facet) per `experiment` and label the axis from `risk_basis`. Saffire-II: "Average flame spread (mm/s)". FLEX: "Share of tests where the flame kept burning", with `oxygen_pct` on the x axis or as colour. Put `tests` and the outcome counts on hover. This replaces the "Riskiest materials" chart, which still says "Fake numbers" and is nearly empty on real data (be_notes.md).
- **For BE:** `data/ranking.csv` is a new data file next to `master.csv`. It is not a contract function. If FE would rather get it through the API, a small `get_ranking()` would be a contract change.

## 10. Spot-check against the reports (Day 14, FIF-D14-DAT)

Compared the numbers in the 3 reports (`docs/reports/`) with `data/master.csv` and the clean
tables. The reports are short abstracts, so these are all the numbers they give that the tables
also hold.

| # | Value in the report | In our data | Result |
|---|---|---|---|
| 1 | FLEX-2 pressure "between 0.5 atm to 3.0 atm" | `pressure_kpa_min/max` 50.662 / 303.975 kPa (0.5 / 3.0 atm) | **Match** |
| 2 | FLEX-2 O2 "between 0.1 to 0.4 mole fraction" | `oxygen_pct_min/max` 17 / 30 % | **Differs, kept.** The raw table lists the 4 levels used (0.17, 0.21, 0.25, 0.3). The report gives the chamber's whole range. 17-30 sits inside it |
| 3 | FLEX droplet "≈ 3 mm" | `droplet_diameter_mm` median 3.01 mm (middle half 2.58-3.52) | **Match** |
| 4 | FLEX LOI test pressure "0.5 − 1.5 atm" | 264 tests at 0.69-1.02 atm, 9 at 2.0-3.05 atm | **Differs, kept.** The 9 high ones are all one series: 21% O2, 9% N2, 70% CO2, run 2009-05-22 to 07-01. They aren't LOI tests, so the report's range doesn't cover them. No test ran at 0.5 atm |
| 5 | FLEX suppressants "CO2, He, and SF6" | raw columns `CO` and `He` | **Fixed:** the `CO` column is CO2. Renamed `co_pct` to `co2_pct` |
| 6 | Saffire-II airflow "either 20 or 30 cm/s" | `flow_cm_s_min/max` 20 for all 9 samples | **Match the table, kept.** The raw table runs every sample at 20 cm/s. None of the 9 is at 30 |
| 7 | Saffire-II "9 samples, each 5 cm x 29 cm" | 9 rows; raw length 29 cm, width 5 cm (2-7: 5 + 24 cm) | **Match** |
| 8 | Saffire-II materials: SIBAL, silicone, structure PMMA, flat PMMA, PMMA with Nomex | Silicone 4, SIBAL 2, PMMA 2, PMMA & Nomex 1 | **Differs, not changed yet** (below) |

**Why the `CO` column is CO2 (fix 5):**
- The raw headers drop every subscript: `O` is O2 and `N` is N2. So `CO` is CO2 with the "2" lost.
- The report names CO2, not CO, as a tested suppressant.
- Its values go up to 70%. Carbon monoxide is a toxic fuel gas, not something tested as a fire
  suppressant, let alone at 70%.

The fix touches only `data/clean/flex.csv` (header), `clean_tables.py` and `check_data.py`.
`master.csv` and `ranking.csv` don't have the column and are byte-for-byte unchanged.

**Structure vs flat PMMA (8), not changed yet:** the report names 2 PMMA types, and the table has
exactly 2 PMMA samples (2-8 and 2-9), both labelled `PMMA`. So it's one sample each. Which is
which is an inference: 2-8's thickness is "See Fig. 5" (a shaped sample), and 2-9's is a plain
1 cm (a flat sheet). That suggests 2-8 = structure, 2-9 = flat. The figure is in the "Experimental
Details" file, which we haven't downloaded. Renaming them would split the `PMMA` row in
`ranking.csv` into 2 single-sample rows and change what FE shows, so it waits for that file or a
team decision.

**Not checkable from the reports:** Saffire-II oxygen (the reports give none), and anything about
SF6. No FLEX test in the table used SF6.

**For the app:** FLEX-2's range "17-30%" is the levels used, not the chamber's 10-40% limit. Also,
the FLEX chart's highest pressures (2-3 atm) all come from the CO2 series, so a pressure effect
there is mixed with a CO2 effect.

Tests: `tests/test_spot_check.py` checks each row above. Each test first confirms the report still
says what's quoted, then checks the saved tables, so a report change or cleaning change that breaks
agreement fails CI.
