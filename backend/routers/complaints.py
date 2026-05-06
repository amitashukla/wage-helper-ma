"""Phase 2C — Employer complaint lookup router.

GET /api/complaints/lookup?employer=<name>&threshold=80
"""

from fastapi import APIRouter, Query
from backend.services.complaint_lookup import lookup

router = APIRouter(tags=["complaints"])


@router.get("/complaints/lookup")
async def complaints_lookup(
    employer: str = Query(..., description="Employer name to search for"),
    threshold: int = Query(80, ge=0, le=100, description="Fuzzy match threshold (0-100)"),
) -> dict:
    """Fuzzy-match an employer name and return their complaint records."""
    return {**lookup(employer, threshold=threshold), "query": employer}
