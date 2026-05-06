"""
Phase 1B — Extract text from AG publication PDFs, chunk, tag, and embed.

Inputs:
  - data/publications/*.pdf (downloaded by download_publications.py)
  - data/publications/manifest.json (metadata for each PDF)

Outputs:
  - embeddings/publication_embeddings_v{YYYYMMDD}.npy
  - embeddings/publication_chunks_v{YYYYMMDD}.json
"""

import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pdfplumber
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from download_publications import DOCUMENTS

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATUTE_VERSION = os.getenv("STATUTE_VERSION", date.today().strftime("%Y%m%d"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLICATIONS_DIR = PROJECT_ROOT / "data" / "publications"
MANIFEST_FILE = PUBLICATIONS_DIR / "manifest.json"
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
OUTPUT_EMBEDDINGS = EMBEDDINGS_DIR / f"publication_embeddings_v{STATUTE_VERSION}.npy"
OUTPUT_CHUNKS = EMBEDDINGS_DIR / f"publication_chunks_v{STATUTE_VERSION}.json"

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
    "domestic violence leave",
    "labor trafficking",
    "personnel records",
    "vacation pay",
]


def title_to_slug(title: str) -> str:
    """Convert a document title to a filesystem-safe slug."""
    slug = title.lower()
    for ch in ["&", ":", "'", "’", ",", ".", "?", "/"]:
        slug = slug.replace(ch, "")
    slug = slug.replace(" ", "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def approx_token_count(text: str) -> int:
    """Rough token count using whitespace splitting (adequate for chunking heuristic)."""
    return len(text.split())


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF using pdfplumber."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def split_into_sections(text: str) -> list[str]:
    """
    Split text on section/heading boundaries first (double newlines or heading patterns),
    then return non-empty segments.
    """
    # Split on double newlines or lines that look like headings (ALL CAPS lines, numbered headings)
    heading_pattern = r"\n{2,}|(?=\n[A-Z][A-Z\s]{4,}\n)|(?=\n\d+\.\s+[A-Z])"
    segments = re.split(heading_pattern, text)
    return [s.strip() for s in segments if s and s.strip()]


def chunk_text_with_overlap(text: str, slug: str, title: str, category: str) -> list[dict]:
    """
    Chunk document text respecting token limits.
    - Split on section/paragraph boundaries first.
    - If a segment exceeds MAX_TOKENS, split further on paragraph boundaries with overlap.
    """
    sections = split_into_sections(text)
    chunks = []
    current_tokens: list[str] = []
    current_parts: list[str] = []

    def finalize_chunk():
        """Save the current accumulated text as a chunk."""
        if current_parts:
            chunk_text = "\n\n".join(current_parts)
            chunks.append(
                {
                    "source": "publication",
                    "slug": slug,
                    "category": category,
                    "title": title,
                    "chunk_index": len(chunks),
                    "text": chunk_text,
                    "tags": [],
                }
            )

    for section in sections:
        section_tokens = section.split()

        # If this single section exceeds MAX_TOKENS, handle it specially
        if approx_token_count(section) > MAX_TOKENS:
            # Finalize anything accumulated so far
            finalize_chunk()
            current_tokens = []
            current_parts = []

            # Split the large section by paragraph boundaries (single newlines)
            paragraphs = re.split(r"\n+", section)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]

            para_tokens: list[str] = []
            para_parts: list[str] = []

            for para in paragraphs:
                para_word_list = para.split()
                if para_tokens and (len(para_tokens) + len(para_word_list)) > MAX_TOKENS:
                    # Finalize this sub-chunk
                    chunk_text = "\n\n".join(para_parts)
                    chunks.append(
                        {
                            "source": "publication",
                            "slug": slug,
                            "category": category,
                            "title": title,
                            "chunk_index": len(chunks),
                            "text": chunk_text,
                            "tags": [],
                        }
                    )
                    # Overlap: keep last OVERLAP_TOKENS
                    overlap = " ".join(para_tokens[-OVERLAP_TOKENS:])
                    para_tokens = overlap.split()
                    para_parts = [overlap]

                para_tokens.extend(para_word_list)
                para_parts.append(para)

            # Finalize remaining paragraphs
            if para_parts:
                chunk_text = "\n\n".join(para_parts)
                chunks.append(
                    {
                        "source": "publication",
                        "slug": slug,
                        "category": category,
                        "title": title,
                        "chunk_index": len(chunks),
                        "text": chunk_text,
                        "tags": [],
                    }
                )
            continue

        # Normal case: check if adding this section exceeds limit
        if current_tokens and (len(current_tokens) + len(section_tokens)) > MAX_TOKENS:
            finalize_chunk()
            # Overlap: keep last OVERLAP_TOKENS from the finalized chunk
            overlap = " ".join(current_tokens[-OVERLAP_TOKENS:])
            current_tokens = overlap.split()
            current_parts = [overlap]

        current_tokens.extend(section_tokens)
        current_parts.append(section)

    # Finalize last chunk
    finalize_chunk()

    # Force-split any chunk that still exceeds MAX_TOKENS (e.g., single giant paragraph)
    final_chunks = []
    for chunk in chunks:
        if approx_token_count(chunk["text"]) > MAX_TOKENS * 1.5:
            words = chunk["text"].split()
            for start in range(0, len(words), MAX_TOKENS - OVERLAP_TOKENS):
                segment = " ".join(words[start : start + MAX_TOKENS])
                final_chunks.append(
                    {
                        "source": "publication",
                        "slug": chunk["slug"],
                        "category": chunk["category"],
                        "title": chunk["title"],
                        "chunk_index": len(final_chunks),
                        "text": segment,
                        "tags": [],
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


def build_manifest_from_documents() -> list[dict]:
    """Build publication metadata from DOCUMENTS when manifest is missing/empty."""
    manifest = []
    for doc in DOCUMENTS:
        slug = title_to_slug(doc["title"])
        manifest.append(
            {
                "slug": slug,
                "title": doc["title"],
                "category": doc["category"],
                "url": doc["url"],
            }
        )
    return manifest


def main():
    manifest: list[dict]
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if manifest:
            logger.info(f"Loaded manifest with {len(manifest)} entries.")
        else:
            logger.warning(
                "Manifest exists but is empty. Falling back to DOCUMENTS metadata."
            )
            manifest = build_manifest_from_documents()
    else:
        logger.warning(
            f"Manifest not found: {MANIFEST_FILE}. Falling back to DOCUMENTS metadata."
        )
        manifest = build_manifest_from_documents()

    logger.info(f"Using {len(manifest)} publication metadata entries.")

    all_chunks: list[dict] = []
    processed = 0
    skipped = 0

    for entry in manifest:
        slug = entry["slug"]
        title = entry["title"]
        category = entry["category"]
        pdf_path = PUBLICATIONS_DIR / f"{slug}.pdf"

        if not pdf_path.exists():
            logger.warning(f"PDF not found for '{slug}', skipping.")
            skipped += 1
            continue

        # Extract text
        text = extract_text_from_pdf(pdf_path)

        # Flag suspiciously short extractions (likely scanned image PDFs)
        if len(text) < 100:
            logger.warning(
                f"Suspiciously short text ({len(text)} chars) extracted from "
                f"'{slug}' — may be a scanned image PDF."
            )
            if not text.strip():
                skipped += 1
                continue

        # Chunk the document
        chunks = chunk_text_with_overlap(text, slug, title, category)

        # Tag each chunk
        for chunk in chunks:
            chunk["tags"] = tag_chunk(chunk["text"])

        all_chunks.extend(chunks)
        processed += 1

    logger.info(
        f"Processed {processed} PDFs, skipped {skipped}. "
        f"Created {len(all_chunks)} chunks total."
    )

    if not all_chunks:
        logger.error("No chunks produced. Exiting.")
        sys.exit(1)

    # Embed all chunks
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    texts = [chunk["text"] for chunk in all_chunks]
    logger.info(f"Encoding {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    embeddings = np.array(embeddings, dtype=np.float32)

    # Save outputs
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    np.save(OUTPUT_EMBEDDINGS, embeddings)
    logger.info(f"Saved embeddings: {OUTPUT_EMBEDDINGS} (shape: {embeddings.shape})")

    with open(OUTPUT_CHUNKS, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved chunk metadata: {OUTPUT_CHUNKS}")

    # Summary
    tagged_count = sum(1 for c in all_chunks if c["tags"])
    logger.info(f"{tagged_count}/{len(all_chunks)} chunks have at least one keyword tag.")
    logger.info("Done.")


if __name__ == "__main__":
    main()
