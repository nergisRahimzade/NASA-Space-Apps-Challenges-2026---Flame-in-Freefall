# Flame in Freefall — Contract v1.10

Everyone codes against these shapes. Change them only by pull request, and bump the version.

**v1.1:** `search()` returns 5 chunks by default instead of 3 (FIF-D11-AI, `tests/top_k.md`).

**v1.2 (FIF-D09-BE):** `get_table()` reads the real `data/master.csv`. Oxygen, pressure and airflow
are min/max pairs, `material_category`, `spread_rate_per_flow` and `outcome` are new, empty cells are
`None`, and there is a `material_category` filter. Chunks also carry their `experiment` (Day 12).

**v1.3 (FIF-D10-BE):** `search()` is real: it ranks the report chunks (`data/processed/chunks.jsonl`)
and each result also has the chunk's `experiment`. The first search after a deploy builds the index
(about 15 s); later searches take well under a second.

**v1.4 (FIF-D12-BE):** `search()` takes an optional `experiment` filter, so results can come from
one experiment only. Calls without it work exactly as before.

**v1.5 (FIF-D13-BE):** `search()` leaves out results scoring under 0.30, so an off-topic question
returns `[]` ("no match") and can return fewer than k. All three functions reject malformed input
(non-text query, a k that isn't a whole number above 0, passages that aren't chunk dicts, filters
that aren't a dict) with `ValueError`.

**v1.6 (FIF-D15-BE):** `summarize()`'s shape is unchanged, but now it's guaranteed on every path
(Gemini, the quoting fallback, nothing found): each takeaway has exactly `text`, `source` and
`chunk_id`, all non-empty text. A passage's `id`, `text` and `source` must be non-empty text, or
`ValueError`. The plan asks for `{takeaways: [{text, source}]}`. We keep `chunk_id` (it's how a
takeaway is checked against its passage) and `not_found`.

**v1.7 (FIF-D15-AI):** `summarize()` takes an optional `question` (the user's search text). With
it, the summary keeps only takeaways that help answer the question, and `not_found` is True when
no passage does, even if the passages are about fire. Calls without it work exactly as before.
A `question` that is blank or not text -> `ValueError`. The return shape is unchanged.

**v1.8 (FIF-D16-DAT):** BASS-II is the 4th experiment: 129 more `master.csv` rows (419 in all)
and 4 more report chunks (22), so `experiment` can also be `"BASS-II"` in `get_table()`,
`search()` and the chunks. `outcome` can also be `Blowoff` (blown out by strong airflow) or
`No ignition` (BASS-II only). Rows have 2 more columns, `suppressant` (`none`, `CO2` or `He`)
and `suppressant_pct`, after the airflow columns. The existing rows and their values don't
change.

**Data freeze (FIF-D17-DAT):** `master.csv` is frozen as **data v1.0** (Git tag `data-v1.0`,
record in `data/freeze.json`). From here on, `get_table()` returns the same 419 rows and 14
columns. A change to them needs the team's agreement and a new data version, and CI
(`tests/test_freeze.py`) fails until one is recorded. The function signatures don't change.

**v1.9 (FIF-D16-BE):** the backend protects itself. A `query` (`search()`) or `question`
(`summarize()`) of more than 300 characters, counted after trimming spaces (`api.MAX_QUERY_CHARS`),
raises `ValueError`; the app's search box stops at 300, so visitors never see the error.
`summarize()` sends at most 10 requests a minute to Gemini, shared by all visitors (setting
`GEMINI_CALLS_PER_MINUTE`); past that, the takeaways are quoted from the passages, exactly as with
no key or when Gemini fails, so the return shape doesn't change. A Gemini request that never
answers now ends after about 32 seconds (15 s per try, 2 tries) instead of about 95. `search()` has
no timeout of its own: its only slow case is the one-time index build after a deploy.

**v1.10 (FIF-D17-BE):** a repeated `summarize()` call returns the remembered answer: the same
question (capitals and spaces ignored), the same passages in the same order, the same prompt and
model give the answer Gemini gave the first time, instantly, without a Gemini call and without
counting against the 10-a-minute limit. Only answers Gemini gave are remembered (a "not found"
included), never the quoting fallback, and the memory holds the latest 256. With no Gemini key
set, the passages are quoted as before, even for a remembered question. The return shape
doesn't change. Each Gemini call's token counts are logged to `artifacts/usage.log`
(`uv run python -m flame_in_freefall.usage` reports them); the optional settings
`GEMINI_USD_PER_M_INPUT` and `GEMINI_USD_PER_M_OUTPUT` add a cost.

## 1. Functions (in `src/flame_in_freefall/api.py`)

```python
def search(query: str, k: int = 5, experiment: str | None = None) -> list[dict]:
    """Return up to k best-matching report chunks for a question, best first.
    Each item: {"id", "text", "source", "page", "score", "experiment"}
    (score: cosine similarity as a float, higher = better;
    experiment: FLEX-2, Saffire-II, FLEX or BASS-II)
    Only results scoring at least 0.30 (api.MIN_SCORE) are returned, so fewer than k is normal,
    and no match (an off-topic question) -> [].
    experiment: "FLEX-2", "Saffire-II", "FLEX" or "BASS-II" keeps only that experiment's chunks (before
    ranking, so all results come from it); None (the default) searches every experiment.
    Empty, blank or non-text query, a query over 300 characters, k that isn't a whole number
    above 0, a blank experiment, or an unknown experiment -> ValueError (the message lists the
    valid experiments, or the length and the limit).
    The first call builds the search index if it's missing or older than chunks.jsonl,
    so it can take ~15 s."""


def summarize(passages: list[dict], question: str | None = None) -> dict:
    """Turn found passages into takeaways that cite their chunk.
    question: the user's question (v1.7). Given -> only takeaways that answer it, and
    not_found=True when no passage does. None -> takeaways about anything fire-related.
    passages: a list of chunk dicts with at least "id", "text", "source" and "page"
    (search() results work as they are; extra fields are fine).
    Returns {"takeaways": [{"text": str, "source": str, "chunk_id": str}], "not_found": bool}
    Every takeaway has exactly these 3 keys, each non-empty text; chunk_id is one of the
    passages' ids and source is that passage's source. not_found is True only when there are
    no takeaways.
    No passages -> {"takeaways": [], "not_found": True}.
    When Gemini isn't used (no key, over the 10-a-minute limit, or it failed), each takeaway is
    the first full sentence of its passage, quoted word for word.
    Not a list, a passage that isn't a dict or misses a field, a passage whose id, text or
    source isn't non-empty text, or a question over 300 characters -> ValueError."""


def get_table(filters: dict | None = None) -> list[dict]:
    """Return rows of data/master.csv that match the filters, one dict per row (section 3).
    filters keys (all optional): "experiment" (str), "material" (str),
    "material_category" (str), "oxygen_min" (float), "oxygen_max" (float).
    Text filters match exactly. A row matches the oxygen filters when its oxygen range
    (oxygen_pct_min..oxygen_pct_max) overlaps the filter's range.
    Empty cells are None. No matching rows -> []. None or {} -> every row.
    filters that aren't a dict, an unknown key, blank text, a non-number oxygen value, or
    oxygen_min > oxygen_max -> ValueError."""
```

## 2. Chunk fields (`chunks.jsonl`, one JSON object per line)

| field  | type | example |
|--------|------|---------|
| id     | str  | `bass-001-p3-c0` (doc-page-chunk number) |
| text   | str  | the passage text |
| source | str  | document name, as listed in `sources.csv` |
| page   | int  | page number in the original document |
| experiment | str | `FLEX-2`, `Saffire-II`, `FLEX` or `BASS-II`, from `sources.csv` (Day 12, 16) |

## 3. `master.csv` columns

419 rows: FLEX-2 (8), Saffire-II (9), FLEX (273), BASS-II (129, v1.8). Full definitions are in `data_notes.md` and
`docs/column_dictionary.md`. A source with one value puts the same number in `_min` and `_max`.

| column | unit | meaning | empty when |
|--------|------|---------|------------|
| experiment | — | `FLEX-2`, `Saffire-II`, `FLEX` or `BASS-II` | never |
| material | — | sample material or fuel | never |
| material_category | — | `hydrocarbon`, `alcohol`, `plastic`, `fabric`, `silicone` or `plastic + fabric` | never |
| oxygen_pct_min / oxygen_pct_max | % | oxygen concentration (range) | never |
| pressure_kpa_min / pressure_kpa_max | kPa | ambient pressure (range) | Saffire-II, BASS-II, one FLEX test |
| flow_cm_s_min / flow_cm_s_max | cm/s | airflow speed past the sample (range; FLEX = 0) | some BASS-II rows (`_min` 43, `_max` 6) |
| suppressant | — | fire-suppressing gas added: `none`, `CO2` or `He` (v1.8) | FLEX-2 |
| suppressant_pct | % | that gas's share of the mix; 0 when `none` (v1.8) | FLEX-2 |
| spread_rate_mm_s | mm/s | flame spread rate | all but 2 Saffire-II rows |
| spread_rate_per_flow | — | spread rate ÷ airflow speed (both mm/s) | all but 2 Saffire-II rows |
| outcome | — | `Extinction`, `Completion`, `Disruption`, `Blowoff` or `No ignition` | FLEX-2, Saffire-II, 101 BASS-II rows (not recorded) |

## 4. Mock files
- `data/mock/chunks.mock.jsonl` — 3 fake chunks. No longer used by `search()` since v1.3; kept for
  `tests/test_mock_data.py`.
- `data/mock/master.mock.csv` — 5 fake rows with the v1.0 columns. No longer used by `get_table()`
  since v1.2; kept for `tests/test_mock_data.py`.
