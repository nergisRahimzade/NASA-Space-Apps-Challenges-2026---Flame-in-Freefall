# Data card: Flame in Freefall experiment data

**Version:** data v1.0 (frozen 2026-11-10, recorded in `data/freeze.json`, Git tag `data-v1.0`)
**Main file:** `data/master.csv`: 419 rows, 14 columns, 4 experiments
**Built for the question** (`docs/the_question.md`): *At what oxygen levels and airflow speed does
a fire in space keep burning or go out, for different materials?*

This card is the short version: what the data is, where it came from, how to rebuild it and what
it can't tell you. The reasons behind each decision are in `data_notes.md`, and every column is
defined in `docs/column_dictionary.md`.

## 1. Sources

All four tables come from NASA's Physical Science Informatics (PSI) repository. Each is the
experiment's "Experimental table" CSV, saved unchanged in `data/raw/` (listed in
`data/downloads.csv`).

| Experiment | What was burned | PSI page | Raw file | Downloaded | Rows |
|---|---|---|---|---|---|
| FLEX-2 | 8 liquid fuels (droplets) | https://psi.nasa.gov/physci/repo/data/investigations/PSI-68 | `PSI-68_Experimental table_Flex2.csv` | 2026-11-03 | 8 |
| Saffire-II | 9 solid samples (fabric, PMMA, silicone) | https://psi.nasa.gov/physci/repo/data/investigations/PSI-99 | `PSI-99_Experimental table_SAFFIRE-2.csv` | 2026-11-03 | 9 |
| FLEX | Heptane and methanol droplets | https://psi.nasa.gov/physci/repo/data/investigations/PSI-69 | `PSI-69_Experimental table_FLEX.csv` | 2026-11-03 | 273 |
| BASS-II | 129 burns of solid samples in a small wind tunnel | https://psi.nasa.gov/physci/repo/data/investigations/PSI-25 | `PSI-25_Experimental table_BASS-II.csv` | 2026-11-10 | 129 |
| | | | | **Total** | **419** |

**Report text for search:** one investigation description per experiment, from the same four PSI
pages, in `docs/reports/*_abstract.txt` (listed in `data/sources.csv`).

## 2. What one row means

| Experiment | One row is | Measured, or planned? |
|---|---|---|
| FLEX-2 | One fuel, with the **ranges** of oxygen, pressure and airflow planned for it | Planned ranges, not test results |
| Saffire-II | One burned sample | Measured |
| FLEX | One droplet test | Measured |
| BASS-II | One burn (`test_id`; the same sample can appear in several burns) | Measured |

Oxygen, pressure and airflow are stored as **min and max columns**. A single value goes in both.

## 3. Columns of `master.csv`

| Column | Unit | Meaning |
|---|---|---|
| `experiment` | | FLEX-2, Saffire-II, FLEX or BASS-II |
| `material` | | Fuel or sample material |
| `material_category` | | Group such as hydrocarbon, alcohol, fabric, plastic |
| `oxygen_pct_min`, `oxygen_pct_max` | % | Oxygen level |
| `pressure_kpa_min`, `pressure_kpa_max` | kPa | Ambient pressure (empty for Saffire-II and BASS-II) |
| `flow_cm_s_min`, `flow_cm_s_max` | cm/s | Airflow past the sample (0 for FLEX droplets) |
| `suppressant` | | Fire-suppressing gas added to the mix: `none`, `CO2` or `He` (empty for FLEX-2) |
| `suppressant_pct` | % | How much of that gas was in the mix |
| `spread_rate_mm_s` | mm/s | Measured flame spread rate |
| `spread_rate_per_flow` | | Spread rate divided by airflow (no unit) |
| `outcome` | | How a test ended: `Extinction`, `Completion`, `Disruption`, `Blowoff`, `No ignition` |

Full definitions, where each value comes from and how messy values were cleaned:
`docs/column_dictionary.md`.

**Derived file:** `data/ranking.csv` (30 groups) ranks risk **within** Saffire-II (average flame
spread) and FLEX (share of finished tests where the flame kept burning). Ranks from different
experiments can't be compared. Details: `data_notes.md` section 9.

## 4. How the data is built

From `data/raw/` to the files the app reads, in this order:

1. `clean_tables`: fixes messy values and units, writes `data/clean/*.csv` (one per experiment).
2. `build_master`: combines the clean tables into `data/master.csv`.
3. `build_ranking`: groups the tests and ranks them, writes `data/ranking.csv`.
4. `check_data`: range and duplicate checks on every file.

**Re-run from scratch** (from the repo root, in a fresh clone):

```bash
uv sync --locked
uv run --locked python -m flame_in_freefall.freeze_data
```

`freeze_data` runs the four steps above in order, then compares every file with
`data/freeze.json`. The expected ending is `master.csv v1.0 (419 rows): re-run matches the
freeze.`, and `git status` should show no changed files. Each step can also be run on its own,
for example `uv run --locked python -m flame_in_freefall.clean_tables`.

**Search side (not part of the data freeze):** `uv run --locked python -m flame_in_freefall.ingest
--force` rebuilds the report chunks (`data/processed/chunks.jsonl`, 22 chunks) and the search
index (`artifacts/index/`).

**Checked on 2026-11-12:** a fresh clone of `main` ran both commands. Every data file came out
identical to the frozen one, `check_data` found no problems, and all tests passed.

## 5. Known limits

These shape what the app can honestly say:

- **Spread rate exists for 2 of 419 rows** (Saffire-II's cotton-fiberglass fabric, SIBAL). The
  Saffire-II ranking uses burn length ÷ burn time instead, which may read a little low.
- **FLEX-2 holds planned ranges, not results.** It has no outcome, so it isn't ranked.
- **FLEX has no airflow** (droplets in still air), and 173 of its 273 tests had CO2 or helium
  added, which lowers how often a flame keeps burning.
- **Saffire-II covers one oxygen level** (about 22%) and one airflow (20 cm/s), so it ranks
  materials but says nothing about oxygen.
- **BASS-II:** how a burn ended is recorded for 28 of 129 tests, and the airflow at which a flame
  went out is known in cm/s for only 3 of its 20 extinctions. Crews lowered the airflow until
  flames went out on purpose, so BASS-II isn't in the ranking.
- **Small groups:** some ranking groups rest on 1–4 tests. The app shows the counts on hover.
- **Pressure is missing** for Saffire-II and BASS-II.

## 6. Versions and changes

- `data/freeze.json` holds a fingerprint (SHA-256), row count and columns for every built file,
  and a fingerprint for each raw table. `tests/test_freeze.py` fails in CI if any of them change.
- To get this exact data later: `git checkout data-v1.0`.
- Changing the data after the freeze needs the team's agreement, then a new version:
  `uv run --locked python -m flame_in_freefall.freeze_data --write --version 1.1`, a note in
  `data_notes.md` and a new tag. Details: `data_notes.md` section 14.
- `tests/test_data_card.py` checks that this card's version, row counts and links still match
  `data/freeze.json` and `data/downloads.csv`.

## 7. Credits

Experiment data and report text are from NASA's Physical Science Informatics repository
(https://psi.nasa.gov), from the FLEX, FLEX-2, Saffire-II and BASS-II investigations.
This project cleaned and combined them. NASA has not reviewed or endorsed this project or its
conclusions. Licence and terms of use are checked in FIF-D25-DAT.
