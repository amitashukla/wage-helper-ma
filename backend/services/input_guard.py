"""
Lightweight pattern-based off-topic filter.
No LLM call — pure keyword matching.
"""

import re
from typing import Optional

_REDIRECT_MESSAGE = (
    "This tool is specific to Massachusetts wage theft. For other legal questions, "
    "please visit [mass.gov legal aid resources](https://www.mass.gov/finding-legal-aid)."
)

# Keywords that always mark a message as on-topic, regardless of other matches.
_ON_TOPIC_KEYWORDS = [
    "wage",
    "pay",
    "salary",
    "overtime",
    "tip",
    "minimum wage",
    "worker",
    "employee",
    "employer",
    "fired",
    "retaliation",
    "sick leave",
    "earned sick",
    "prevailing wage",
    "independent contractor",
]

# Off-topic category definitions: (category_name, [keyword_patterns])
_OFF_TOPIC_CATEGORIES = [
    (
        "medical",
        [
            "malpractice",
            "doctor",
            "hospital",
            "diagnosis",
            "prescription",
            "surgery",
            "mental health counseling",
        ],
    ),
    (
        "immigration",
        [
            "visa application",
            "deportation",
            "citizenship",
            "green card",
            "asylum",
            "immigration court",
        ],
    ),
    (
        "criminal",
        [
            "criminal charges",
            "arrest",
            "bail",
            "parole",
            "probation",
            "felony",
            "misdemeanor",
            "dui",
        ],
    ),
    (
        "family_law",
        [
            "divorce",
            "custody",
            "child support",
            "alimony",
            "adoption",
        ],
    ),
    (
        "housing",
        [
            "eviction",
            "landlord",
            "lease",
            "rent dispute",
            "tenant",
        ],
    ),
]


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for consistent matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _contains_any(text: str, keywords: list[str]) -> bool:
    for kw in keywords:
        if kw in text:
            return True
    return False


def check(message: str) -> dict:
    """
    Returns {"is_valid": bool, "redirect_message": Optional[str]}.

    A message is valid if it is on-topic (wage/employment keywords present)
    or does not match any off-topic category.
    """
    normalized = _normalize(message)

    # If the message contains any on-topic keyword, always allow it.
    if _contains_any(normalized, _ON_TOPIC_KEYWORDS):
        return {"is_valid": True, "redirect_message": None}

    # Check each off-topic category.
    for _category, keywords in _OFF_TOPIC_CATEGORIES:
        if _contains_any(normalized, keywords):
            return {"is_valid": False, "redirect_message": _REDIRECT_MESSAGE}

    # No off-topic pattern matched — allow by default.
    return {"is_valid": True, "redirect_message": None}
