"""Groq LLM client wrapper.

Uses httpx (sync) to call the Groq chat completions endpoint.
Model: llama-3.3-70b-versatile
"""

import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root (backend/services -> backend -> root)
# ---------------------------------------------------------------------------
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "llama-3.3-70b-versatile"
_TEMPERATURE = 0.2
_MAX_TOKENS = 1024
_TIMEOUT = 30.0  # seconds

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LLMUnavailableError(Exception):
    """Raised when the Groq API is unreachable or returns a non-200 response."""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def build_prompt(
    system_prompt: str,
    few_shot_examples: str,
    session_summary: str,
    statute_chunks: list[dict],
    conversation_history: list[dict],
    user_message: str,
) -> list[dict]:
    """Build an OpenAI-style messages list for the Groq API.

    Structure:
      1. System message  (system_prompt)
      2. Few-shot examples parsed as alternating user/assistant turns
      3. Statute context injected as a system message
      4. Last 8 turns from conversation_history
      5. Current user message

    Args:
        system_prompt:        Contents of backend/prompts/system.txt.
        few_shot_examples:    Contents of backend/prompts/few_shot.txt.
                              Expected format: alternating lines starting with
                              "User:" and "Assistant:" separated by blank lines.
        session_summary:      Short description of session context, e.g.
                              "Employer: Dunkin Donuts. Violation: Overtime."
        statute_chunks:       Retrieved statute chunks from statute_search,
                              each a dict with keys: section_id, text, score, etc.
        conversation_history: List of {role, content} dicts (full history).
                              Only the last 8 turns are included.
        user_message:         The current user query.

    Returns:
        List of message dicts ready to POST to the Groq API.
    """
    messages: list[dict] = []

    # 1. System message
    messages.append({"role": "system", "content": system_prompt.strip()})

    # 2. Few-shot examples as alternating user/assistant turns
    few_shot_turns = _parse_few_shot(few_shot_examples)
    messages.extend(few_shot_turns)

    # 3. Statute context as a system message
    statute_context = _build_statute_context(statute_chunks, session_summary)
    if statute_context:
        messages.append({"role": "system", "content": statute_context})

    # 4. Last 8 turns of conversation history
    recent_history = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
    messages.extend(recent_history)

    # 5. Current user message
    messages.append({"role": "user", "content": user_message})

    return messages


def _parse_few_shot(few_shot_examples: str) -> list[dict]:
    """Parse few-shot text into alternating user/assistant message dicts.

    Expects blocks separated by blank lines where each block starts with
    "User:" or "Assistant:" (case-insensitive). Lines within a block that
    do not start with a role prefix are treated as continuation of the
    previous role.
    """
    if not few_shot_examples or not few_shot_examples.strip():
        return []

    turns: list[dict] = []
    current_role: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_role and current_lines:
            turns.append({"role": current_role, "content": "\n".join(current_lines).strip()})

    for line in few_shot_examples.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("user:"):
            _flush()
            current_role = "user"
            current_lines = [stripped[5:].strip()]
        elif lower.startswith("assistant:"):
            _flush()
            current_role = "assistant"
            current_lines = [stripped[10:].strip()]
        else:
            if current_role is not None:
                current_lines.append(stripped)

    _flush()
    return turns


def _build_statute_context(statute_chunks: list[dict], session_summary: str) -> str:
    """Format statute chunks and session summary into a context block."""
    parts: list[str] = []

    if session_summary and session_summary.strip():
        parts.append(f"Session context: {session_summary.strip()}")

    if statute_chunks:
        parts.append("Relevant statute sections retrieved for this query:")
        for chunk in statute_chunks:
            section_id = chunk.get("section_id", "unknown")
            section_title = chunk.get("section_title", "")
            text = chunk.get("text", "")
            score = chunk.get("score")

            header = f"[{section_id}]"
            if section_title:
                header += f" {section_title}"
            if score is not None:
                header += f" (relevance: {score:.3f})"

            parts.append(f"{header}\n{text.strip()}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------


def complete(messages: list[dict]) -> str:
    """POST messages to the Groq chat completions endpoint and return the reply.

    Args:
        messages: OpenAI-style list of message dicts.

    Returns:
        The assistant's reply as a plain string.

    Raises:
        LLMUnavailableError: On HTTP error, timeout, or missing API key.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise LLMUnavailableError("GROQ_API_KEY is not set in environment.")

    payload = {
        "model": _MODEL,
        "messages": messages,
        "temperature": _TEMPERATURE,
        "max_tokens": _MAX_TOKENS,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.post(_GROQ_API_URL, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        logger.error("Groq API request timed out: %s", exc)
        raise LLMUnavailableError("Groq API request timed out.") from exc
    except httpx.RequestError as exc:
        logger.error("Groq API request error: %s", exc)
        raise LLMUnavailableError(f"Groq API request failed: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "Groq API returned status %d: %s",
            response.status_code,
            response.text[:500],
        )
        raise LLMUnavailableError(
            f"Groq API returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        logger.error("Unexpected Groq API response shape: %s", exc)
        raise LLMUnavailableError("Unexpected response format from Groq API.") from exc
