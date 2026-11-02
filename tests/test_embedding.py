from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = genai.Client()  # reads GEMINI_API_KEY from your environment
texts = ["My dog loves walks", "Puppies enjoy going outside", "Tax forms are due in April"]
res = client.models.embed_content(model="gemini-embedding-001", contents=texts)
vecs = [np.array(e.values) for e in res.embeddings]


def sim(a, b):
    return a @ b / (np.linalg.norm(a) * np.linalg.norm(b))


print(sim(vecs[0], vecs[1]))  # should be high (similar meaning)
print(sim(vecs[0], vecs[2]))  # should be lower
