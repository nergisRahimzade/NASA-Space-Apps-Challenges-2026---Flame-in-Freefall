import csv
import json
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parents[1] / "data" / "mock"
CHUNK_FIELDS = {"id": str, "text": str, "source": str, "page": int}
MASTER_COLUMNS = [
    "experiment",
    "material",
    "oxygen_pct",
    "pressure_kpa",
    "flow_cm_s",
    "spread_rate_mm_s",
]


def test_mock_chunks_match_contract():
    lines = (MOCK_DIR / "chunks.mock.jsonl").read_text().splitlines()
    chunks = [json.loads(line) for line in lines if line.strip()]
    assert len(chunks) == 3
    for chunk in chunks:
        assert chunk.keys() == CHUNK_FIELDS.keys()
        for field, kind in CHUNK_FIELDS.items():
            assert isinstance(chunk[field], kind)


def test_mock_master_matches_contract():
    with open(MOCK_DIR / "master.mock.csv", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert reader.fieldnames == MASTER_COLUMNS
    assert len(rows) == 5
