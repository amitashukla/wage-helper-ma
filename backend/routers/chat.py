"""Chat router — POST /api/chat

Accepts a user message and an optional session profile, runs the RAG
orchestrator, and returns the assistant reply plus updated session state.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.rag import orchestrate
from backend.session.schema import SessionProfile

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session: SessionProfile = SessionProfile()


@router.post("/chat")
async def chat(body: ChatRequest) -> dict:
    """Run the RAG pipeline and return the assistant response.

    Request body:
        message: str              — the user's chat message
        session: SessionProfile   — optional; defaults to an empty session

    Response:
        answer:             str
        citation_blocks:    list[dict]
        violation_category: str | None
        employer_matches:   list[str]
        confidence_flag:    "high" | "low" | "fallback"
        session:            dict  (updated SessionProfile)
    """
    return orchestrate(user_message=body.message, session=body.session)
