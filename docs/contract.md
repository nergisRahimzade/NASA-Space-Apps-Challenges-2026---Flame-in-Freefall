# Flame in Freefall — Contract v1.0

Everyone codes against these shapes. Change them only by pull request, and bump the version.

## 1. Functions (in `src/flame_in_freefall/api.py`)

```python
def search(query: str, k: int = 3) -> list[dict]:
    """Return the k best-matching chunks for a question, best first.
    Each item: {"id", "text", "source", "page", "score"}  (score: float, higher = better)
    Empty or blank query -> ValueError."""


def summarize(passages: list[dict]) -> dict:
    """Turn found passages into takeaways that cite their chunk.
    Returns {"takeaways": [{"text": str, "source": str, "chunk_id": str}], "not_found": bool}
    No passages -> {"takeaways": [], "not_found": True}."""


def get_table(filters: dict | None = None) -> list[dict]:
    """Return rows of master.csv that match the filters.
    filters keys (all optional): "experiment" (str), "material" (str),
    "oxygen_min" (float), "oxygen_max" (float). Unknown key -> ValueError."""
```

## 2. Chunk fields (`chunks.jsonl`, one JSON object per line)

| field  | type | example |
|--------|------|---------|
| id     | str  | `bass-001-p3-c0` (doc-page-chunk number) |
| text   | str  | the passage text |
| source | str  | document name, as listed in `sources.csv` |
| page   | int  | page number in the original document |

## 3. `master.csv` columns

| column | unit | meaning |
|--------|------|---------|
| experiment | — | BASS, FLEX or Saffire |
| material | — | sample material |
| oxygen_pct | % | oxygen concentration |
| pressure_kpa | kPa | ambient pressure |
| flow_cm_s | cm/s | airflow speed past the sample |
| spread_rate_mm_s | mm/s | flame spread rate |

## 4. Mock files
- `data/mock/chunks.mock.jsonl` — 3 fake chunks
- `data/mock/master.mock.csv` — 5 fake rows (numbers are made up, for building only)
