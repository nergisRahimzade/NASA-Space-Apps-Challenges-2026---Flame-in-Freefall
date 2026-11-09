# Column dictionary (Day 5, FIF-D05-DAT)

Raw tables in `data/raw/`, inspected with `scripts/day5_inspect_tables.py`.
Linked to the question in `the_question.md`: *at what oxygen levels and airflow speed does a fire in space keep burning or go out, for different materials?*

**Cross-table summary**

| Question variable | FLEX-2 (PSI-68) | FLEX (PSI-69) | Saffire-II (PSI-99) |
|---|---|---|---|
| Material / fuel | Fuel type | Fuel (Methanol, Heptane) | Material |
| Oxygen | Oxygen mole fraction (range) | O mole fraction (per test) | Percent O2 (per test, approximate) |
| Airflow | Flow velocity (range) | none | Air flow (all 20 cm/s) |
| Outcome | none | Test end, burning rate, burn time | Burn time, spread rate/length |

Units differ across tables (mole fraction vs %, mmHg vs atm), so Day 8 cleaning must normalise them.

## 1. PSI-68 FLEX-2: `PSI-68_Experimental table_Flex2.csv`

8 rows x 7 columns. This is a **test matrix** (planned conditions, as ranges), not measurements. One row per fuel, and every condition column is identical across rows except fuel. Nothing is missing.

| Column | Type in file | Unit | Meaning / example |
|---|---|---|---|
| Sample (Fuel Type) | text | n/a | Fuel droplet, pure or mixture with percentages, e.g. `Heptane (50%) IsoOctane (50%) (mixture)` |
| Initial Droplet Diameter (mm) | text range | mm | `1.5 - 5` |
| Ambient Gas Mixture | text | n/a | `O2/N2 or O2/He` |
| Oxygen Mole Fraction | text list | fraction (0-1) | `0.17; 0.21;0.25; 0.3` (set of values) |
| Ambient Pressure (atm) | text list | atm | `0.5; 1.0; 1.5; 2.0; or 3.0` |
| Ambient Temperature (C) | int | deg C | `25` |
| Flow Velocity (cm/s) | text range | cm/s | `0.1 - 5` |

Issues: values are ranges/lists in text and need parsing (`min`/`max` or exploding to one row per value); header `Ambient Gas Mixture ` and ` Ambient Temperature (C)` have stray spaces. No outcome column, so it can't show burn vs. extinguish by itself.

## 2. PSI-69 FLEX: `PSI-69_Experimental table_FLEX.csv`

274 rows x 15 columns. One row per test: the only table with per-test numeric oxygen and outcomes. Droplet combustion of methanol (157 tests) and heptane (117), in microgravity, with no airflow.

| Column | Type in file | Unit | Missing / bad | Meaning |
|---|---|---|---|---|
| FLEX Test # | int | n/a | 0 | Row number 1-274 |
| FLEX Identifier | text | n/a | 1 duplicate | Test ID, e.g. `20CAL08`. `193F001` appears twice (rows 70, 73) with different values |
| Test Date | text | M/D/YYYY or M/D/YY | 0 | Mixed 2- and 4-digit years (`10/24/09`) |
| Test GMT | text | hh:mm:ss GMT | 1 | Test time |
| Fuel | text | n/a | 0 | `Methanol` or `Heptane` |
| Ambient pressure; mmHg | float | mmHg (760 = 1 atm) | 1 zero (`C11M201`) | Chamber pressure, 526 to 2320 mmHg; 0 is impossible, treat as missing |
| O initial ambient composition; mole fraction | float | fraction | 0 | Oxygen, 0.12 to 0.34 |
| N initial ambient composition; mole fraction | float | fraction | 0 | Nitrogen |
| CO initial ambient composition; mole fraction | float | fraction | 0 | Likely CO2 (diluent, up to 0.7); header says CO. **Assumption, confirm in the report** |
| He initial ambient composition; mole fraction | float | fraction | 0 | Helium |
| Droplet initial diameter; mm | text | mm | 6 empty + 6 `�` | Starting droplet size. `�` is a corrupted character for "no value" |
| Visible flame extinction diameter; mm | text | mm | 49 empty + 28 `�` | Droplet diameter when flame went out. `0` is a real value (burned to the end) |
| Burning rate; mm | float | header says mm, expect mm^2/s | 16 | Droplet burning rate (0.05 to 1.06). **Unit looks wrong in the header**, confirm in the report |
| Burn time; s | text | s | 6 empty, 2 `~6` / `~9` | Duration of burning |
| Test end | text | n/a | 0 | Outcome: Extinction (186), Disruption (61), Completion (27) |

Reading the outcome: **Extinction** = flame went out (the "went out" case in our question). **Completion** = fuel burned out. **Disruption** = test interrupted (for example droplet disturbed), so it is not a clean burn or extinguish result and should probably be excluded from outcome analysis (assumption: confirm).

Issues to fix on Day 8: `�` and `~` values in numeric columns, 1 duplicate ID, 1 zero pressure, mmHg to atm, mole fraction to percent, dates to one format, column names to snake_case.

## 3. PSI-99 Saffire-II: `PSI-99_Experimental table_SAFFIRE-2.csv`

15 rows x 17 columns. Only 9 real samples (`2-1` to `2-9`). The last 6 rows are 2 pre-test flow-visualization rows (`F1C1/F1C2`, `F2C1/F2C2`) and 4 footnotes (Notes 1-4, referenced from cells), which must be dropped when loading but whose text should be kept as documentation. Burning of solid sheets on the ISS.

| Column | Type in file | Unit (embedded in text) | Meaning / example |
|---|---|---|---|
| Sample Number | text | n/a | `2-1`. Footer rows reuse this column for notes |
| Material | text | n/a | Silicone, Cotton-Fiberglass (SIBAL), PMMA, PMMA & Nomex. 2 empty (`2-6`, `2-9`): same material as the row above (SIBAL and PMMA) |
| Samle Thickness | text | mm, cm | Header typo "Samle". `0.27 mm`, `1 cm`, `037 mm` (typo for 0.37), `See Fig. 5` |
| Sample Length | text | cm | `29 cm`, `5 and 24 cm` |
| Sample Width (cm) | text | cm | `5 cm` (unit in the value too) |
| Air Flow (cm/s) | text | cm/s | `20 cm/s`, constant in every test |
| Percent O2 (Note 1) | text | % | `~ 21.5`, `22.1 to 22.0`. Approximate and derived from CO2 production |
| Ignition Power (W) | text | W | `80 W`, `97 W` |
| Ignition Time (s) | text | s | `9.2 s`, `30 s` |
| Burn Time (s) | text | s | `145 s`, or `Insignificant` |
| Flow Direction | text | n/a | `Concurrent` or `Opposed` |
| ?-g Burn Length | text | cm | Header's `?` is a corrupted micro sign, so this is **microgravity (µ-g)** burn length. `~ 0`, `29 cm` |
| ?-g Spread Length | text | mm/s (despite the name) | `2.1 mm/s`, `n/a`. Looks like a spread **rate**, header says length, confirm |
| 1-g Burn Length | text | cm | Earth-gravity comparison. `Complete`, `7.6 cm`, `~ 0` |
| 1-g Spread Rate | text | mm/s | `1.2 mm/s`, `Acceleratory`, `n/a` |
| Camera 1 / Camera 2 | text | n/a | Video file labels (`S1C1`). Not analytical, can be dropped |

Issues: every number is text with units inside; `~`, `n/a`, `Note 4`, `Insignificant`, `Complete` and `Acceleratory` mix words with numbers; only 4 distinct O2 values, 1 airflow value, so Saffire-II can't show an airflow effect on its own. Burn outcome has to be derived (for example `~ 0` burn length means flame did not spread = went out).

## 4. Added columns in `master.csv` (Day 11, FIF-D11-DAT)

These two columns are not in any raw table. `build_master.py` works them out from the other master columns. The rest of `master.csv` is listed in `data_notes.md` section 2.

| Column | Type | Unit | Meaning |
|---|---|---|---|
| `material_category` | text | n/a | The group a material belongs to, so charts can compare like with like. Never empty. |
| `spread_rate_per_flow` | float | none (ratio) | `spread_rate_mm_s` / (airflow in cm/s x 10), so both sides are in mm/s. How fast the flame moves compared with the air blowing past it: `0.0105` means 1/95th as fast. |

**`material_category` values**

| Category | Kind | Materials | Experiments |
|---|---|---|---|
| `hydrocarbon` | liquid fuel | Heptane, IsoOctane, n-Octane, Decane, Heptane (50%) IsoOctane (50%) | FLEX-2, FLEX (Heptane) |
| `alcohol` | liquid fuel | Methanol, Ethanol, Propanol (95%) Glycerol (5%), Propanol (80%) Glycerol (20%) | FLEX-2, FLEX (Methanol) |
| `plastic` | solid sheet | PMMA (acrylic, Plexiglas) | Saffire-II |
| `fabric` | solid sheet | Cotton-Fiberglass (SIBAL) | Saffire-II |
| `silicone` | solid sheet | Silicone (silicone rubber) | Saffire-II |
| `plastic + fabric` | solid sheet | PMMA & Nomex (PMMA with Nomex, a fire-resistant fabric) | Saffire-II |

Rules:
- A mixture goes with its parts: Propanol and Glycerol are both alcohols, Heptane and IsoOctane are both hydrocarbons.
- The lookup is `MATERIAL_CATEGORY` in `src/flame_in_freefall/build_master.py`. If a material is not in it, the build stops with an error instead of leaving the category empty.

**`spread_rate_per_flow` filled rows:** only the 2 Saffire-II SIBAL samples (`2-5`: 2.1 mm/s / 200 mm/s = 0.0105, `2-6`: 2.6 / 200 = 0.013). It is empty when:
- there is no spread rate (all of FLEX-2 and FLEX, and the other Saffire-II samples),
- the airflow is 0 (FLEX), so there is nothing to divide by,
- the airflow is a range (FLEX-2, 0.1-5 cm/s), so there is no single number to divide by.

Why spread / airflow and not a 0-1 scale: with only 2 spread rates, a 0-1 scale would just turn them into 0 and 1. The ratio keeps its meaning, and it can still be compared if tests at other airflow speeds are added.

## 5. Riskiness ranking: `data/ranking.csv` (Day 13, FIF-D13-DAT)

Built by `src/flame_in_freefall/build_ranking.py` from `data/master.csv` and `data/clean/saffire2.csv`. One row = one experiment + material + oxygen level. 30 rows: Saffire-II 4, FLEX 26. Rules and reasons: `data_notes.md` section 9.

| Column | Type | Unit | Meaning |
|---|---|---|---|
| `experiment` | text | n/a | `Saffire-II` or `FLEX`. FLEX-2 is left out (no results, only planned ranges). |
| `material` | text | n/a | Same spelling as `master.csv`. |
| `material_category` | text | n/a | Same as `master.csv` (section 4). |
| `oxygen_pct` | number | % | Oxygen level of the group: middle of `oxygen_pct_min`/`max`, rounded to a whole percent (0.5 rounds up). |
| `tests` | integer | count | Rows of `master.csv` in the group (Saffire-II samples or FLEX tests). |
| `spread_rate_n` | integer | count | How many of those rows have a measured `spread_rate_mm_s`. Only SIBAL (2). |
| `spread_rate_mm_s_min` / `_mean` / `_max` | number | mm/s | Smallest, average and largest measured spread rate. Empty when `spread_rate_n` is 0. |
| `burn_spread_mm_s_mean` | number | mm/s | Saffire-II only. Average spread over the whole burn: microgravity burn length / burn time, averaged over the samples. 0 when the flame did not spread (burn length 0). Empty for FLEX. |
| `completion` / `extinction` / `disruption` | integer | count | FLEX only. How many tests ended each way (`master.csv` `outcome`). Empty for Saffire-II, which has no outcome. |
| `kept_burning_share` | number | 0-1 | FLEX only. `completion / (completion + extinction)`: of the tests that finished, the share where the flame burned until the fuel was gone instead of going out. Disruptions are left out. |
| `risk_basis` | text | n/a | Name of the column that decides the rank: `burn_spread_mm_s_mean` (Saffire-II) or `kept_burning_share` (FLEX). |
| `risk_value` | number | as `risk_basis` | Copy of that column, so a chart can plot one column for both experiments. |
| `risk_rank` | integer | n/a | 1 = riskiest **within the experiment**. Ties share a rank (two groups at 1.0 are both 1, the next is 3). Do not compare ranks across experiments. |

## Gaps and risks for the project

- **Airflow** exists only as a range in FLEX-2 and as a constant in Saffire-II; FLEX has none. A "which airflow" answer will be thin.
- **Oxygen + material + outcome in the same table** exists only in FLEX (fuel, O fraction, Test end). Saffire-II has O2 and material but outcome is derived. FLEX-2 has no outcome.
- Master table (Day 9) will likely be one row per test: FLEX rows plus Saffire-II samples; FLEX-2 may be reference only.
- `data/downloads.csv` is out of date: it lists `PSI-69_Experimental table_Flex.csv` (actual name `..._FLEX.csv`) and folders like `data/raw/flex2/`, but the files sit directly in `data/raw/`. Fix one or the other.
