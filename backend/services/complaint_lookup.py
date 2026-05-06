"""Phase 2C — Employer complaint lookup via fuzzy matching.

Loaded once at module import time:
  - employer_index.json  {normalized_name: {original_names: [...], row_ids: [...]}}
  - complaints.json      array of complaint record dicts (positional index = row_id)

Usage:
    from backend.services.complaint_lookup import lookup
    results = lookup("Dunkin Donuts", threshold=80)
"""

import json
import re
from pathlib import Path

from rapidfuzz import process as rf_process

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_EMPLOYER_INDEX_PATH = _PROJECT_ROOT / "data" / "processed" / "employer_index.json"
_COMPLAINTS_PATH = _PROJECT_ROOT / "data" / "processed" / "complaints.json"

# ---------------------------------------------------------------------------
# Module-level data — loaded once at startup
# ---------------------------------------------------------------------------

with open(_EMPLOYER_INDEX_PATH, encoding="utf-8") as _f:
    _employer_index: dict[str, dict] = json.load(_f)

with open(_COMPLAINTS_PATH, encoding="utf-8") as _f:
    _complaints: list[dict] = json.load(_f)

# Pre-build the list of normalized keys for RapidFuzz to search against.
_index_keys: list[str] = list(_employer_index.keys())

# ---------------------------------------------------------------------------
# Normalization — mirrors ingest_complaints.py exactly
# ---------------------------------------------------------------------------

_ABBREV_PAIRS = [
    (re.compile(r"\bd/b/a\b"), "doing business as"),
    (re.compile(r"\bllc\b"), "limited liability company"),
    (re.compile(r"\binc\b"), "incorporated"),
    (re.compile(r"\bcorp\b"), "corporation"),
    (re.compile(r"\bltd\b"), "limited"),
    (re.compile(r"\bco\b"), "company"),
    (re.compile(r"\bdba\b"), "doing business as"),
]

_PUNCT_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_employer(name: str) -> str:
    """Normalize an employer name the same way ingestion does.

    Steps: strip → lowercase → remove punctuation → collapse whitespace →
           expand common abbreviations (applied in order).
    """
    out = name.strip().lower()
    out = _PUNCT_RE.sub("", out)
    out = _WHITESPACE_RE.sub(" ", out).strip()
    for pattern, replacement in _ABBREV_PAIRS:
        out = pattern.sub(replacement, out)
    return out


# ---------------------------------------------------------------------------
# Public lookup function
# ---------------------------------------------------------------------------


def lookup(employer_name: str, threshold: int = 80) -> dict:
    """Fuzzy-search the employer index and return matching complaint records.

    Args:
        employer_name: Raw employer name string supplied by the caller.
        threshold:     Minimum RapidFuzz score (0–100) to include a match.
                       Defaults to 80.

    Returns:
        {
            "matches": [
                {
                    "matched_employer": str,   # normalized index key
                    "original_names":   list,  # distinct raw spellings
                    "match_score":      float,
                    "complaints":       list[dict],
                },
                ...
            ]
        }
        An empty "matches" list is returned when no results exceed threshold.
    """
    if not employer_name or not employer_name.strip():
        return {"matches": []}

    normalized_query = normalize_employer(employer_name)
    if not normalized_query:
        return {"matches": []}

    # RapidFuzz: top-10 candidates, scorer defaults to WRatio
    raw_results = rf_process.extract(
        normalized_query,
        _index_keys,
        limit=10,
        score_cutoff=threshold,
    )

    if not raw_results:
        return {"matches": []}

    matches = []
    for matched_key, score, _idx in raw_results:
        entry = _employer_index[matched_key]
        row_ids: list[int] = entry["row_ids"]
        complaint_records = [_complaints[rid] for rid in row_ids if rid < len(_complaints)]
        matches.append(
            {
                "matched_employer": matched_key,
                "original_names": entry["original_names"],
                "match_score": round(score, 2),
                "complaints": complaint_records,
            }
        )

    # Sort descending by score so the best match comes first
    matches.sort(key=lambda m: m["match_score"], reverse=True)

    return {"matches": matches}
