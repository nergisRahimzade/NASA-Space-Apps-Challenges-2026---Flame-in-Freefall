"""Day 1 (AI): prove the embedding model and the Gemini key both work.

Run from the project root:  uv run --env-file .env python scripts/day1_check_ai.py
Without a .env (no key yet):  uv run python scripts/day1_check_ai.py  (skips the Gemini part)
The first run downloads the embedding model (~90 MB) from Hugging Face; later runs use the cache."""

import httpx
from google import genai
from google.genai import errors
from sentence_transformers import SentenceTransformer

from flame_in_freefall.config import get_settings, setup_logging

log = setup_logging()
# Same settings the app uses, so this checks the exact models the app will run with.
settings = get_settings()

# 1) Embeddings: 2 sentences -> 2 vectors (all-MiniLM-L6-v2 gives 384 numbers each).
model = SentenceTransformer(settings.embed_model)
vectors = model.encode(
    [
        "Flames spread differently in microgravity.",
        "Without gravity there is no buoyant airflow to feed a fire.",
    ]
)
log.info("Embedding shape: %s", vectors.shape)  # expect (2, 384)
# Similarity near 1 = same meaning, near 0 = unrelated; these two should score fairly high.
log.info("Similarity: %.3f", float(model.similarity(vectors[0:1], vectors[1:2])[0][0]))

# 2) One test prompt to Gemini. None = no key set yet, so skip instead of crashing.
if settings.gemini_api_key is None:
    log.warning("GEMINI_API_KEY not set: skipped the test prompt (add it to .env, then rerun)")
else:
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents="In one sentence, why do flames look round in microgravity?",
        )
        log.info("Gemini (%s) says: %s", settings.gemini_model, response.text)
    # Bad key, unknown model, no connection... show the reason instead of a long traceback.
    except (errors.APIError, httpx.TransportError) as e:
        log.error("Test prompt failed: %s", e)
