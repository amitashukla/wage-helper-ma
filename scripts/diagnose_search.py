import os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import numpy as np
from sentence_transformers import SentenceTransformer

VERSION = os.getenv("STATUTE_VERSION", "")
EMB_DIR = Path(__file__).parent.parent / "embeddings"

chunks = json.load(open(EMB_DIR / f"statute_chunks_v{VERSION}.json"))
embeddings = np.load(EMB_DIR / f"statute_embeddings_v{VERSION}.npy").astype("float32")
print(f"Loaded {len(chunks)} chunks, embeddings shape: {embeddings.shape}")

model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))

queries = [
    "My employer didn't pay me for overtime",
    "I never get a pay stub",
    "My boss pays me less than minimum wage",
]

for q in queries:
    vec = model.encode(q, convert_to_numpy=True).astype("float32")
    vec /= np.linalg.norm(vec) + 1e-10
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10
    scores = (embeddings / norms) @ vec
    top = np.argsort(-scores)[:5]
    print(f"\nQuery: {q!r}")
    for i in top:
        print(f"  {scores[i]:.3f}  [{chunks[i].get('section_id','')}] {chunks[i].get('text','')[:80]}")