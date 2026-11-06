# Flame in Freefall — Contract v1.3

Everyone codes against these shapes. Change them only by pull request, and bump the version.

**v1.1:** `search()` returns 5 chunks by default instead of 3 (FIF-D11-AI, `tests/top_k.md`).

**v1.2 (FIF-D09-BE):** `get_table()` reads the real `data/master.csv`. Oxygen, pressure and airflow
are min/max pairs, `material_category`, `spread_rate_per_flow` and `outcome` are new, empty cells are
`None`, and there is a `material_category` filter. Chunks also carry their `experiment` (Day 12).

**v1.3 (FIF-D10-BE):** `search()` is real: it ranks the report chunks (`data/processed/chunks.jsonl`)
and each result also has the chunk's `experiment`. The first search after a deploy builds the index
(about 15 s); later searches take well under a second.

## 1. Functions (in `src/flame_in_freefall/api.py`)

```python
def search(query: str, k: int = 5) -> list[dict]:
    """Return the k best-matching report chunks for a question, best first.
    Each item: {"id", "text", "source", "page", "score", "experiment"}
    (score: cosine similarity as a float, higher = better; experiment: FLEX-2, Saffire-II or FLEX)
    Empty or blank query -> ValueError. The first call builds the search index if it's missing
    or older than chunks.jsonl, so it can take ~15 s."""


def summarize(passages: list[dict]) -> dict:
    """Turn found passages into takeaways that cite their chunk.
    Returns {"takeaways": [{"text": str, "source": str, "chunk_id": str}], "not_found": bool}
    No passages -> {"takeaways": [], "not_found": True}."""


def get_table(filters: dict | None = None) -> list[dict]:
    """Return rows of data/master.csv that match the filters, one dict per row (section 3).
    filters keys (all optional): "experiment" (str), "material" (str),
    "material_category" (str), "oxygen_min" (float), "oxygen_max" (float).
    Text filters match exactly. A row matches the oxygen filters when its oxygen range
    (oxygen_pct_min..oxygen_pct_max) overlaps the filter's range.
    Empty cells are None. No matching rows -> [].
    Unknown key, blank text, a non-number oxygen value, or oxygen_min > oxygen_max -> ValueError."""
```

## 2. Chunk fields (`chunks.jsonl`, one JSON object per line)

| field  | type | example |
|--------|------|---------|
| id     | str  | `bass-001-p3-c0` (doc-page-chunk number) |
| text   | str  | the passage text |
| source | str  | document name, as listed in `sources.csv` |
| page   | int  | page number in the original document |
| experiment | str | `FLEX-2`, `Saffire-II` or `FLEX`, from `sources.csv` (Day 12) |

## 3. `master.csv` columns

290 rows: FLEX-2 (8), Saffire-II (9), FLEX (273). Full definitions are in `data_notes.md` and
`docs/column_dictionary.md`. A source with one value puts the same number in `_min` and `_max`.

| column | unit | meaning | empty when |
|--------|------|---------|------------|
| experiment | — | `FLEX-2`, `Saffire-II` or `FLEX` | never |
| material | — | sample material or fuel | never |
| material_category | — | `hydrocarbon`, `alcohol`, `plastic`, `fabric`, `silicone` or `plastic + fabric` | never |
| oxygen_pct_min / oxygen_pct_max | % | oxygen concentration (range) | never |
| pressure_kpa_min / pressure_kpa_max | kPa | ambient pressure (range) | Saffire-II, one FLEX test |
| flow_cm_s_min / flow_cm_s_max | cm/s | airflow speed past the sample (range; FLEX = 0) | never |
| spread_rate_mm_s | mm/s | flame spread rate | all but 2 Saffire-II rows |
| spread_rate_per_flow | — | spread rate ÷ airflow speed (both mm/s) | all but 2 Saffire-II rows |
| outcome | — | `Extinction`, `Completion` or `Disruption` | FLEX-2 and Saffire-II |

## 4. Mock files
- `data/mock/chunks.mock.jsonl` — 3 fake chunks. No longer used by `search()` since v1.3; kept for
  `tests/test_mock_data.py`.
- `data/mock/master.mock.csv` — 5 fake rows with the v1.0 columns. No longer used by `get_table()`
  since v1.2; kept for `tests/test_mock_data.py`.
