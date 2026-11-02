"""Day 4 (BE): the index saved by store.py comes back exactly as it went in."""

import json

import numpy as np
import pytest

from flame_in_freefall.store import load_index, save_index

CHUNKS = [
    {"id": "bass-001-p3-c0", "text": "Flame spread at 21% O₂.", "source": "BASS", "page": 3},
    {"id": "flex-002-p1-c0", "text": "Droplet burned 2 s.", "source": "FLEX", "page": 1},
]


def test_round_trip(tmp_path):
    vectors = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], dtype=np.float32)
    save_index(vectors, CHUNKS, tmp_path)
    loaded_vectors, loaded_chunks = load_index(tmp_path)
    np.testing.assert_array_equal(loaded_vectors, vectors)
    assert loaded_vectors.dtype == np.float32
    assert loaded_chunks == CHUNKS


def test_save_rejects_count_mismatch(tmp_path):
    with pytest.raises(ValueError):
        save_index(np.zeros((3, 4)), CHUNKS, tmp_path)


def test_save_rejects_1d_vectors(tmp_path):
    with pytest.raises(ValueError):
        save_index(np.zeros(2), CHUNKS, tmp_path)


def test_load_missing_index_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_index(tmp_path / "nothing-here")


def test_load_rejects_mismatched_files(tmp_path):
    save_index(np.zeros((2, 4)), CHUNKS, tmp_path)
    (tmp_path / "chunks.json").write_text(json.dumps(CHUNKS[:1]))
    with pytest.raises(ValueError):
        load_index(tmp_path)
