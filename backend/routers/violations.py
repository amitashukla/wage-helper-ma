"""
violations.py

Router: POST /api/violations/map

Request body : {"text": str}
Response     : {"matches": [...], "text": str}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.violation_mapper import map_violation

router = APIRouter(prefix="/violations", tags=["violations"])


class ViolationMapRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Free-form complaint text to classify")


class ViolationMatch(BaseModel):
    category: str
    score: float


class ViolationMapResponse(BaseModel):
    matches: list[ViolationMatch]
    text: str


@router.post("/map", response_model=ViolationMapResponse)
def map_violation_endpoint(body: ViolationMapRequest) -> ViolationMapResponse:
    """Embed the complaint text and return the top matching AG violation
    categories with cosine-similarity scores."""
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="text must not be blank")

    result = map_violation(body.text)
    return ViolationMapResponse(matches=result["matches"], text=body.text)
