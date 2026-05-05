"""
Phase 1C — Chunk, tag, and embed MA Chapter 149 statute sections.

Inputs:  data/statutes/chapter149_v{YYYYMMDD}.json
Outputs:
  - embeddings/statute_embeddings_v{YYYYMMDD}.npy
  - embeddings/statute_chunks_v{YYYYMMDD}.json
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

STATUTE_VERSION = os.getenv("STATUTE_VERSION", date.today().strftime("%Y%m%d"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "statutes" / f"chapter149_v{STATUTE_VERSION}.json"
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
OUTPUT_EMBEDDINGS = EMBEDDINGS_DIR / f"statute_embeddings_v{STATUTE_VERSION}.npy"
OUTPUT_CHUNKS = EMBEDDINGS_DIR / f"statute_chunks_v{STATUTE_VERSION}.json"

MAX_TOKENS = 512
OVERLAP_TOKENS = 50

# Predefined legal keyword tags
LEGAL_TAGS = [
    "treble damages",
    "meal period",
    "prevailing wage",
    "minimum wage",
    "overtime",
    "retaliation",
    "tips",
    "pay stub",
    "final pay",
    "Sunday pay",
    "holiday pay",
    "deductions",
    "child labor",
    "domestic worker",
    "earned sick time",
    "independent contractor",
]


def approx_token_count(text: str) -> int:
    """Rough token count using whitespace splitting (adequate for chunking heuristic)."""
    return len(text.split())


def split_into_paragraphs(text: str) -> list[str]:
    """Split text on double-newlines or paragraph breaks."""
    paragraphs = re.split(r"\n{2,}", text)
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_section(section: dict) -> list[dict]:
    """
    Split a section into chunks respecting token limits.
    - If section fits in MAX_TOKENS, return as single chunk.
    - Otherwise split on paragraph boundaries with OVERLAP_TOKENS overlap.
    """
    text = section["text"]
    section_id = section["section_id"]
    section_title = section["section_title"]

    if approx_token_count(text) <= MAX_TOKENS:
        return [
            {
                "section_id": section_id,
                "section_title": section_title,
                "chunk_index": 0,
                "text": text,
            }
        ]

    paragraphs = split_into_paragraphs(text)
    chunks = []
    current_tokens: list[str] = []
    current_text_parts: list[str] = []
    chunk_index = 0

    for para in paragraphs:
        para_tokens = para.split()
        # If adding this paragraph exceeds limit, finalize current chunk
        if current_tokens and (len(current_tokens) + len(para_tokens)) > MAX_TOKENS:
            chunk_text = "\n\n".join(current_text_parts)
            chunks.append(
                {
                    "section_id": section_id,
                    "section_title": section_title,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                }
            )
            chunk_index += 1

            # Overlap: keep last OVERLAP_TOKENS worth of tokens from current chunk
            overlap_text = " ".join(current_tokens[-OVERLAP_TOKENS:])
            current_tokens = overlap_text.split()
            current_text_parts = [overlap_text]

        current_tokens.extend(para_tokens)
        current_text_parts.append(para)

    # Finalize last chunk
    if current_text_parts:
        chunk_text = "\n\n".join(current_text_parts)
        chunks.append(
            {
                "section_id": section_id,
                "section_title": section_title,
                "chunk_index": chunk_index,
                "text": chunk_text,
            }
        )

    # Handle edge case: single very long paragraph exceeding MAX_TOKENS
    # Split by sentences if any chunk still exceeds limit
    final_chunks = []
    for chunk in chunks:
        if approx_token_count(chunk["text"]) > MAX_TOKENS * 1.5:
            # Force-split by word boundary
            words = chunk["text"].split()
            for start in range(0, len(words), MAX_TOKENS - OVERLAP_TOKENS):
                segment = " ".join(words[start : start + MAX_TOKENS])
                final_chunks.append(
                    {
                        "section_id": chunk["section_id"],
                        "section_title": chunk["section_title"],
                        "chunk_index": len(final_chunks),
                        "text": segment,
                    }
                )
        else:
            chunk["chunk_index"] = len(final_chunks)
            final_chunks.append(chunk)

    return final_chunks


def tag_chunk(text: str) -> list[str]:
    """Return list of matching legal keyword tags found in the chunk text."""
    text_lower = text.lower()
    return [tag for tag in LEGAL_TAGS if tag in text_lower]


def main():
    if not INPUT_FILE.exists():
        print(
            f"ERROR: Statute file not found: {INPUT_FILE}\n"
            f"Run scrape_statute.py first or set STATUTE_VERSION correctly.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        sections = json.load(f)

    print(f"Loaded {len(sections)} sections from {INPUT_FILE.name}")

    # Chunk all sections
    all_chunks = []
    for section in sections:
        chunks = chunk_section(section)
        for chunk in chunks:
            chunk["tags"] = tag_chunk(chunk["text"])
            all_chunks.append(chunk)

    print(f"Created {len(all_chunks)} chunks total.")

    # Embed
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    texts = [chunk["text"] for chunk in all_chunks]
    print(f"Encoding {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    embeddings = np.array(embeddings, dtype=np.float32)

    # Save outputs
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    np.save(OUTPUT_EMBEDDINGS, embeddings)
    print(f"Saved embeddings: {OUTPUT_EMBEDDINGS} (shape: {embeddings.shape})")

    with open(OUTPUT_CHUNKS, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    print(f"Saved chunk metadata: {OUTPUT_CHUNKS}")

    # Summary
    tagged_count = sum(1 for c in all_chunks if c["tags"])
    print(f"\n{tagged_count}/{len(all_chunks)} chunks have at least one keyword tag.")
    print("Done.")


if __name__ == "__main__":
    main()
