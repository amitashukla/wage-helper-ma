"""Statute + publication citation search via semantic similarity.

Loaded once at module import time. Returns empty list if embedding files are
missing so the rest of the app can still start.
"""

import json
import logging
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root (two levels up: backend/services -> backend -> root)
# ---------------------------------------------------------------------------
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_STATUTE_VERSION: str = os.getenv("STATUTE_VERSION", "")
_EMBEDDINGS_DIR = Path(__file__).resolve().parent.parent.parent / "embeddings"

_SCORE_THRESHOLD: float = 0.30

# ---------------------------------------------------------------------------
# Module-level state (populated at import time)
# ---------------------------------------------------------------------------
_model = None          # sentence-transformers SentenceTransformer instance
_corpus_chunks: list[dict] = []   # combined statute + publication chunk metadata
_corpus_embeddings: np.ndarray | None = None  # shape (N, D)
_ready: bool = False   # True only when both model and embeddings loaded successfully


def _load_corpus() -> tuple[list[dict], np.ndarray | None]:
    """Load statute and publication chunks + embeddings. Returns (chunks, embeddings)."""
    if not _STATUTE_VERSION:
        logger.warning(
            "STATUTE_VERSION env var not set — statute search disabled."
        )
        return [], None

    statute_chunks_path = _EMBEDDINGS_DIR / f"statute_chunks_v{_STATUTE_VERSION}.json"
    statute_emb_path = _EMBEDDINGS_DIR / f"statute_embeddings_v{_STATUTE_VERSION}.npy"
    pub_chunks_path = _EMBEDDINGS_DIR / f"publication_chunks_v{_STATUTE_VERSION}.json"
    pub_emb_path = _EMBEDDINGS_DIR / f"publication_embeddings_v{_STATUTE_VERSION}.npy"

    all_chunks: list[dict] = []
    all_embeddings: list[np.ndarray] = []

    for label, chunks_path, emb_path in (
        ("statute", statute_chunks_path, statute_emb_path),
        ("publication", pub_chunks_path, pub_emb_path),
    ):
        if not chunks_path.exists() or not emb_path.exists():
            logger.warning(
                "Embedding files for %s corpus not found (looked for %s and %s) — "
                "skipping this corpus.",
                label,
                chunks_path,
                emb_path,
            )
            continue

        try:
            with open(chunks_path, "r", encoding="utf-8") as fh:
                chunks: list[dict] = json.load(fh)

            embeddings: np.ndarray = np.load(str(emb_path))

            if len(chunks) != embeddings.shape[0]:
                logger.warning(
                    "%s corpus: chunk count (%d) != embedding row count (%d) — skipping.",
                    label,
                    len(chunks),
                    embeddings.shape[0],
                )
                continue

            # Tag each chunk with its corpus source so callers can distinguish
            for chunk in chunks:
                chunk.setdefault("source", label)

            all_chunks.extend(chunks)
            all_embeddings.append(embeddings)
            logger.info("Loaded %d %s chunks.", len(chunks), label)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load %s corpus: %s", label, exc)

    if not all_chunks:
        return [], None

    combined = np.vstack(all_embeddings).astype(np.float32)
    return all_chunks, combined


def _load_model():
    """Load the sentence-transformers model. Returns None on failure."""
    try:
        from sentence_transformers import SentenceTransformer  # local import to avoid slow startup if unused

        logger.info("Loading embedding model: %s", _EMBEDDING_MODEL_NAME)
        model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
        logger.info("Embedding model loaded.")
        return model
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load embedding model (%s): %s", _EMBEDDING_MODEL_NAME, exc)
        return None


# ---------------------------------------------------------------------------
# Startup initialisation (runs once at import)
# ---------------------------------------------------------------------------
_corpus_chunks, _corpus_embeddings = _load_corpus()

if _corpus_embeddings is not None:
    _model = _load_model()
    if _model is not None:
        _ready = True
        logger.info(
            "Statute search ready: %d total chunks, model=%s",
            len(_corpus_chunks),
            _EMBEDDING_MODEL_NAME,
        )
    else:
        logger.warning("Statute search disabled: embedding model failed to load.")
else:
    logger.warning("Statute search disabled: no embedding files found.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search(query: str, top_k: int = 5) -> list[dict]:
    """Return up to *top_k* chunks most relevant to *query*.

    Each result dict contains:
        section_id, section_title, text, tags, score, source

    Returns an empty list when the service is not ready or no chunk exceeds
    the similarity threshold.
    """
    if not _ready or _corpus_embeddings is None or _model is None:
        return []

    query = query.strip()
    if not query:
        return []

    # ------------------------------------------------------------------
    # 1. Keyword pre-filter: candidate chunks must share at least one word
    #    with the query (matched against each chunk's tags list).
    # ------------------------------------------------------------------
    query_words = {w.lower() for w in query.split() if len(w) > 2}

    candidate_indices: list[int] = []
    if query_words:
        for idx, chunk in enumerate(_corpus_chunks):
            tags = chunk.get("tags") or []
            # Match whole tags (e.g. "overtime") or individual words within
            # multi-word tags (e.g. "minimum" or "wage" from "minimum wage"),
            # but only exact tag-word matches — not substring matches.
            tag_words: set[str] = set()
            for t in tags:
                tag_words.add(t.lower())          # whole tag: "pay stub"
                tag_words.update(t.lower().split())  # words: "pay", "stub"
            if query_words & tag_words:
                candidate_indices.append(idx)

    # With only ~500 chunks, cosine similarity over the full corpus is fast.
    # Fall back whenever the tag filter would be too narrow.
    if len(candidate_indices) < 20:
        candidate_indices = list(range(len(_corpus_chunks)))

    candidate_embeddings = _corpus_embeddings[candidate_indices]  # (C, D)

    # ------------------------------------------------------------------
    # 2. Embed the query
    # ------------------------------------------------------------------
    query_vec: np.ndarray = _model.encode(query, convert_to_numpy=True).astype(np.float32)

    # ------------------------------------------------------------------
    # 3. Cosine similarity
    # ------------------------------------------------------------------
    # Normalise
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    cand_norms = np.linalg.norm(candidate_embeddings, axis=1, keepdims=True) + 1e-10
    cand_normalised = candidate_embeddings / cand_norms

    scores: np.ndarray = cand_normalised @ query_norm  # (C,)

    # ------------------------------------------------------------------
    # 4. Threshold filter
    # ------------------------------------------------------------------
    above_threshold = np.where(scores >= _SCORE_THRESHOLD)[0]
    if above_threshold.size == 0:
        return []

    # ------------------------------------------------------------------
    # 5. Top-k sorted by score descending
    # ------------------------------------------------------------------
    sorted_local = above_threshold[np.argsort(-scores[above_threshold])]
    top_local = sorted_local[:top_k]

    results: list[dict] = []
    for local_idx in top_local:
        global_idx = candidate_indices[local_idx]
        chunk = _corpus_chunks[global_idx]
        results.append(
            {
                "section_id": chunk.get("section_id", ""),
                "section_title": chunk.get("section_title") or chunk.get("title", ""),
                "text": chunk.get("text", ""),
                "tags": chunk.get("tags", []),
                "score": float(scores[local_idx]),
                "source": chunk.get("source", "statute"),
            }
        )

    return results
