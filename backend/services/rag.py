"""RAG orchestrator for the MA Wage Helper chatbot.

Coordinates input validation, parallel retrieval, LLM generation,
citation verification, and session state updates for a single chat turn.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from backend.services import input_guard, statute_search, violation_mapper, complaint_lookup
from backend.services import llm as llm_service
from backend.services.llm import LLMUnavailableError
from backend.services import citation_verifier
from backend.session.schema import SessionProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts — loaded once at module import time
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_SYSTEM_PROMPT: str = (_PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")
_FEW_SHOT: str = (_PROMPTS_DIR / "few_shot.txt").read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Fallback helpers
# ---------------------------------------------------------------------------

_FALLBACK_NO_STATUTE = (
    "I wasn't able to find specific statute information for your question. "
    "For free legal help, visit "
    "https://www.mass.gov/info-details/free-wage-theft-legal-clinic"
)

_FALLBACK_LLM_UNAVAILABLE = (
    "The AI service is temporarily unavailable. Please try again in a moment."
)


def _make_fallback(answer: str, session: SessionProfile) -> dict:
    return {
        "answer": answer,
        "confidence_flag": "fallback",
        "citation_blocks": [],
        "violation_category": None,
        "employer_matches": [],
        "session": session.model_dump(),
    }


# ---------------------------------------------------------------------------
# Session summary builder
# ---------------------------------------------------------------------------

def _build_session_summary(session: SessionProfile) -> str:
    parts: list[str] = []
    if session.employer:
        parts.append(f"Employer: {session.employer}")
    if session.employment_type:
        parts.append(f"Employment type: {session.employment_type}")
    if session.hours_per_week is not None:
        parts.append(f"Hours per week: {session.hours_per_week}")
    if session.violation_categories:
        parts.append(f"Known violation categories: {', '.join(session.violation_categories)}")
    if session.complaint_types:
        parts.append(f"Complaint types: {', '.join(session.complaint_types)}")
    return ". ".join(parts)


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------

def orchestrate(user_message: str, session: SessionProfile) -> dict:
    """Run the full RAG pipeline for a single user turn.

    Args:
        user_message: The raw message text from the user.
        session:      Current SessionProfile (treated as immutable here;
                      an updated copy is returned in the result dict).

    Returns:
        {
            "answer":             str,
            "citation_blocks":    list[dict],
            "violation_category": str | None,
            "employer_matches":   list[str],
            "confidence_flag":    "high" | "low" | "fallback",
            "session":            dict  (updated SessionProfile.model_dump())
        }
    """

    # ------------------------------------------------------------------
    # Step 1 — Input guard
    # ------------------------------------------------------------------
    guard_result = input_guard.check(user_message)
    if not guard_result["is_valid"]:
        return _make_fallback(guard_result["redirect_message"], session)

    # ------------------------------------------------------------------
    # Step 2 — Parallel retrieval
    # ------------------------------------------------------------------
    statute_results: list[dict] = []
    violation_result: dict = {"matches": [{"category": "unknown", "score": 0}]}
    complaint_matches: list[dict] = []

    def _fetch_statutes():
        return statute_search.search(user_message)

    def _fetch_violation():
        return violation_mapper.map_violation(user_message)

    def _fetch_complaints():
        if session.employer:
            return complaint_lookup.lookup(session.employer)["matches"]
        return []

    tasks = {
        "statutes": _fetch_statutes,
        "violation": _fetch_violation,
        "complaints": _fetch_complaints,
    }

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                result = future.result()
                if name == "statutes":
                    statute_results = result
                elif name == "violation":
                    violation_result = result
                elif name == "complaints":
                    complaint_matches = result
            except Exception as exc:  # noqa: BLE001
                logger.warning("RAG orchestrator: retrieval task '%s' failed: %s", name, exc)

    # ------------------------------------------------------------------
    # Step 3 — Evaluate retrieval confidence
    # ------------------------------------------------------------------
    top_violation_score: float = 0.0
    top_violation_category: str | None = None
    if violation_result.get("matches"):
        top_match = violation_result["matches"][0]
        top_violation_score = top_match.get("score", 0.0)
        cat = top_match.get("category", "unknown")
        if cat != "unknown":
            top_violation_category = cat

    if not statute_results and top_violation_score == 0:
        return _make_fallback(_FALLBACK_NO_STATUTE, session)

    if statute_results and top_violation_score == 0:
        confidence_flag = "low"
    else:
        confidence_flag = "high"

    # ------------------------------------------------------------------
    # Step 4 — Build session summary
    # ------------------------------------------------------------------
    session_summary = _build_session_summary(session)

    # ------------------------------------------------------------------
    # Step 5 & 6 — Build prompt and call LLM
    # ------------------------------------------------------------------
    messages = llm_service.build_prompt(
        system_prompt=_SYSTEM_PROMPT,
        few_shot_examples=_FEW_SHOT,
        session_summary=session_summary,
        statute_chunks=statute_results,
        conversation_history=session.conversation_history,
        user_message=user_message,
    )

    try:
        response_text = llm_service.complete(messages)
    except LLMUnavailableError as exc:
        logger.error("RAG orchestrator: LLM call failed: %s", exc)
        return _make_fallback(_FALLBACK_LLM_UNAVAILABLE, session)

    # ------------------------------------------------------------------
    # Step 7 — Citation verification
    # ------------------------------------------------------------------
    verified = citation_verifier.verify(response_text, statute_results)

    # ------------------------------------------------------------------
    # Step 8 — Update session
    # ------------------------------------------------------------------
    # Work on a mutable copy so the caller's object is not mutated
    updated = session.model_copy(deep=True)

    updated.conversation_history.append({"role": "user", "content": user_message})
    updated.conversation_history.append({"role": "assistant", "content": verified["response_text"]})
    # Keep only last 8 turns (16 entries)
    if len(updated.conversation_history) > 16:
        updated.conversation_history = updated.conversation_history[-16:]

    if top_violation_category and top_violation_category not in updated.violation_categories:
        updated.violation_categories.append(top_violation_category)

    if complaint_matches:
        updated.employer_matches = [m["matched_employer"] for m in complaint_matches]

    updated.confidence_flag = confidence_flag

    # ------------------------------------------------------------------
    # Step 9 — Return
    # ------------------------------------------------------------------
    return {
        "answer": verified["response_text"],
        "citation_blocks": verified["citation_blocks"],
        "violation_category": top_violation_category,
        "employer_matches": [m["matched_employer"] for m in complaint_matches],
        "confidence_flag": confidence_flag,
        "session": updated.model_dump(),
    }
