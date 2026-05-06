"""
violation_mapper.py

Embeds all AG violation category names at module import time using the
sentence-transformers model specified by the EMBEDDING_MODEL env var
(default: sentence-transformers/all-MiniLM-L6-v2).

At query time, embeds the incoming complaint text and returns the top-3
categories by cosine similarity.  If the top score is below 0.25 the
result is treated as unknown.
"""

import logging
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file:
#   backend/services/violation_mapper.py -> backend/ -> project root)
_root = Path(__file__).resolve().parents[2]
load_dotenv(_root / ".env")

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

VIOLATION_CATEGORIES: list[str] = [
    "Minimum Wage Violation",
    "Overtime Violation",
    "Meal Period Violation",
    "Rest Period Violation",
    "Tip Theft",
    "Tip Pooling Violation",
    "Sunday/Holiday Pay Violation",
    "Prevailing Wage Violation",
    "Failure to Pay Wages",
    "Late Payment of Wages",
    "Bounced Paycheck",
    "Final Pay Violation",
    "Pay Stub Violation",
    "Payroll Record Violation",
    "Misclassification as Independent Contractor",
    "Illegal Deductions",
    "Uniform Cost Deduction",
    "Retaliation",
    "Wrongful Termination",
    "Failure to Reinstate",
    "Child Labor Violation",
    "Minor Working Illegal Hours",
    "Minor Working Without Permit",
    "Minor Working in Prohibited Occupation",
    "Domestic Worker Violation",
    "Earned Sick Time Violation",
    "Small Necessities Leave Violation",
    "Domestic Violence Leave Violation",
    "OSHA 10 Violation",
    "Personnel Records Violation",
    "Unpaid Commissions",
    "Unpaid Vacation Pay",
    "Vacation Policy Violation",
    "Independent Contractor Misclassification",
    "Temp Worker Rights Violation",
    "Prevailing Wage Record Violation",
    "Public Works Violation",
    "Immigrant Worker Rights Violation",
    "Wage Theft",
    "Forced Labor",
    "Labor Trafficking",
    "Record Keeping Violation",
    "Timely Payment Violation",
    "Wage Assignment Violation",
    "Gratuity Violation",
    "Service Charge Violation",
    "On-Call Pay Violation",
    "Reporting Pay Violation",
    "Split Shift Violation",
    "Travel Time Violation",
]

# ---------------------------------------------------------------------------
# Module-level initialisation — runs once at import time
# ---------------------------------------------------------------------------

_model = None
_category_embeddings: np.ndarray | None = None  # shape (N, dim)


def _load_model():
    """Attempt to load the sentence-transformers model.  Returns the model or
    None if the library is unavailable."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("violation_mapper: loaded embedding model '%s'", EMBEDDING_MODEL)
        return model
    except Exception as exc:  # ImportError or model-download failure
        logger.warning(
            "violation_mapper: could not load sentence-transformers model '%s': %s. "
            "map_violation() will always return unknown.",
            EMBEDDING_MODEL,
            exc,
        )
        return None


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a single vector *a* (1-D) and a
    matrix *b* (N x dim).  Returns a 1-D array of length N."""
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norms = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return b_norms @ a_norm


def _initialise():
    global _model, _category_embeddings

    _model = _load_model()
    if _model is None:
        return

    try:
        _category_embeddings = _model.encode(
            VIOLATION_CATEGORIES, convert_to_numpy=True, show_progress_bar=False
        )
        logger.info(
            "violation_mapper: embedded %d violation categories (dim=%d)",
            len(VIOLATION_CATEGORIES),
            _category_embeddings.shape[1],
        )
    except Exception as exc:
        logger.warning(
            "violation_mapper: failed to embed category names: %s. "
            "map_violation() will always return unknown.",
            exc,
        )
        _model = None
        _category_embeddings = None


# Run at import time
_initialise()

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_UNKNOWN_RESULT = {"matches": [{"category": "unknown", "score": 0}]}
_TOP_K = 3
_MIN_SCORE = 0.25


def map_violation(complaint_text: str) -> dict:
    """Embed *complaint_text* and return the top-3 matching AG violation
    categories by cosine similarity.

    Return format::

        {
            "matches": [
                {"category": "Overtime Violation", "score": 0.72},
                {"category": "Failure to Pay Wages", "score": 0.61},
                {"category": "Timely Payment Violation", "score": 0.58},
            ]
        }

    If the top score is below ``_MIN_SCORE`` (0.25), or the model is
    unavailable, returns::

        {"matches": [{"category": "unknown", "score": 0}]}
    """
    if _model is None or _category_embeddings is None:
        return _UNKNOWN_RESULT

    try:
        query_vec: np.ndarray = _model.encode(
            complaint_text, convert_to_numpy=True, show_progress_bar=False
        )
        scores = _cosine_similarity(query_vec, _category_embeddings)

        top_indices = np.argsort(scores)[::-1][:_TOP_K]
        top_matches = [
            {"category": VIOLATION_CATEGORIES[i], "score": round(float(scores[i]), 4)}
            for i in top_indices
        ]

        if top_matches[0]["score"] < _MIN_SCORE:
            return _UNKNOWN_RESULT

        return {"matches": top_matches}

    except Exception as exc:
        logger.warning("violation_mapper: error during map_violation: %s", exc)
        return _UNKNOWN_RESULT
