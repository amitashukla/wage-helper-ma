"""Post-generation citation verifier.

Parses LLM response text for MA statute section references, checks each
against the retrieved statute chunks, surfaces verified citations, and
strips (with a disclaimer note) any that cannot be verified.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for MA statute section references.
#
# Matches any of:
#   § 148                    (bare section symbol)
#   Section 148              (word "Section")
#   s. 148                   (abbreviated "s.")
#   M.G.L. c. 149, § 148    (full citation)
#   c. 149 § 148             (chapter + section)
#
# Section numbers may include sub-sections, e.g. "148A", "148B", "19C", "150".
# ---------------------------------------------------------------------------

# Pattern group that captures the section number (digits + optional letter suffix)
_SECTION_NUM = r"(\d+[A-Za-z]?)"

# All recognized citation forms — order matters (longer forms first)
_CITATION_PATTERNS: list[re.Pattern] = [
    # M.G.L. c. 149, § 148  or  M.G.L. c. 149 § 148
    re.compile(
        r"M\.G\.L\.?\s+c\.\s*149[,\s]+§\s*" + _SECTION_NUM,
        re.IGNORECASE,
    ),
    # c. 149, § 148  or  c. 149 § 148
    re.compile(
        r"c\.\s*149[,\s]+§\s*" + _SECTION_NUM,
        re.IGNORECASE,
    ),
    # § 148
    re.compile(r"§\s*" + _SECTION_NUM),
    # Section 148
    re.compile(r"\bSection\s+" + _SECTION_NUM, re.IGNORECASE),
    # s. 148
    re.compile(r"\bs\.\s*" + _SECTION_NUM, re.IGNORECASE),
]

# How much verbatim statute text to include in citation blocks
_VERBATIM_CHARS = 300


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _get_full_corpus() -> list[dict]:
    """Return the full loaded statute corpus from statute_search (lazy)."""
    try:
        from backend.services.statute_search import _corpus_chunks
        return [c for c in _corpus_chunks if c.get("source") == "statute"]
    except Exception:
        return []


def verify(response_text: str, statute_chunks: list[dict]) -> dict:
    """Verify statute citations in an LLM response against the full corpus.

    Args:
        response_text:  The raw LLM-generated reply.
        statute_chunks: Chunks returned by statute_search (used first;
                        falls back to full corpus for broader lookup).

    Returns:
        {
            "response_text": str,               # cleaned text
            "citation_blocks": [                # verified citations only
                {
                    "section_id": str,
                    "section_title": str,
                    "verbatim_text": str        # first 300 chars of chunk text
                }
            ],
            "hallucinated_citations_removed": bool
        }
    """
    if not response_text:
        return {
            "response_text": response_text,
            "citation_blocks": [],
            "hallucinated_citations_removed": False,
        }

    # Build lookup from retrieved chunks + full corpus for broader coverage
    all_chunks = statute_chunks + _get_full_corpus()
    chunk_index = _build_chunk_index(all_chunks)

    # Extract all cited sections from the response
    cited_sections = _extract_cited_sections(response_text)

    if not cited_sections:
        return {
            "response_text": response_text,
            "citation_blocks": [],
            "hallucinated_citations_removed": False,
        }

    citation_blocks: list[dict] = []
    hallucinated_citations_removed = False
    cleaned_text = response_text

    # Track sections we've already added a block for (avoid duplicates)
    seen_sections: set[str] = set()

    for section_num, match_text in cited_sections:
        normalised = _normalise_section(section_num)
        chunk = _find_chunk(normalised, chunk_index)

        if chunk is not None:
            # Verified — add citation block (once per unique section)
            if normalised not in seen_sections:
                seen_sections.add(normalised)
                verbatim = chunk.get("text", "")[:_VERBATIM_CHARS]
                citation_blocks.append(
                    {
                        "section_id": chunk.get("section_id", f"§ {section_num}"),
                        "section_title": chunk.get("section_title", ""),
                        "verbatim_text": verbatim,
                    }
                )
        else:
            # Unverified — strip citation reference and append disclaimer
            logger.warning("Citation §%s could not be verified in retrieved chunks.", section_num)
            hallucinated_citations_removed = True
            note = (
                f"[Note: citation §{section_num} could not be verified"
                " — please confirm with a legal professional.]"
            )
            # Replace the exact match text with the note (first occurrence only,
            # to keep replacement local; subsequent occurrences also replaced).
            cleaned_text = cleaned_text.replace(match_text, note)

    return {
        "response_text": cleaned_text,
        "citation_blocks": citation_blocks,
        "hallucinated_citations_removed": hallucinated_citations_removed,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_chunk_index(statute_chunks: list[dict]) -> dict[str, dict]:
    """Return a dict keyed by normalised section identifiers."""
    index: dict[str, dict] = {}
    for chunk in statute_chunks:
        raw_id = chunk.get("section_id", "")
        if not raw_id:
            continue
        # Store under several normalised keys to maximise lookup hit rate
        for key in _normalise_keys(raw_id):
            if key not in index:
                index[key] = chunk
    return index


def _normalise_keys(section_id: str) -> list[str]:
    """Generate lookup keys from a chunk's section_id.

    section_id examples: "149:148", "§ 148", "Section 148", "148"
    """
    keys: list[str] = []
    s = section_id.strip()
    keys.append(s.lower())

    # If it contains a colon (e.g. "149:148"), also store just the number part
    if ":" in s:
        parts = s.split(":", 1)
        keys.append(parts[-1].strip().lower())

    # Strip leading § or "Section " or "s."
    for prefix in ("§", "section", "s."):
        stripped = s.lower().lstrip("§ ").strip()
        if stripped:
            keys.append(stripped)
        break  # only strip once

    # Digits only (e.g. "148")
    digits = re.search(r"(\d+[a-z]?)", s, re.IGNORECASE)
    if digits:
        keys.append(digits.group(1).lower())

    return list(set(keys))


def _normalise_section(section_num: str) -> str:
    """Return a canonical lowercase key for a parsed section number."""
    return section_num.strip().lower()


def _find_chunk(normalised_section: str, chunk_index: dict[str, dict]) -> dict | None:
    """Look up a section in the chunk index, trying several key forms."""
    if normalised_section in chunk_index:
        return chunk_index[normalised_section]

    # Also try zero-padded or un-padded forms, and with/without letter suffix
    candidates = [
        normalised_section,
        normalised_section.lstrip("0"),
        f"§ {normalised_section}",
        f"section {normalised_section}",
        f"149:{normalised_section}",
    ]
    for candidate in candidates:
        if candidate in chunk_index:
            return chunk_index[candidate]

    return None


def _extract_cited_sections(text: str) -> list[tuple[str, str]]:
    """Return a list of (section_number, matched_text) tuples from the response.

    Each tuple is deduplicated by (section_number, matched_text) but preserves
    all distinct match strings (a section may be cited in multiple forms).
    """
    results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            section_num = match.group(1)  # captured section number
            match_text = match.group(0)   # full matched string
            key = (section_num.lower(), match_text)
            if key not in seen:
                seen.add(key)
                results.append((section_num, match_text))

    return results
