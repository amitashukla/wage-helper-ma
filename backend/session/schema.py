from typing import List, Optional
from pydantic import BaseModel


class SessionProfile(BaseModel):
    employer: Optional[str] = None
    employer_matches: List[str] = []
    complaint_types: List[str] = []
    employment_type: Optional[str] = None   # "hourly" | "salary" | "tipped"
    hours_per_week: Optional[float] = None
    violation_categories: List[str] = []
    conversation_history: List[dict] = []   # last 8 turns: [{role, content}]
    confidence_flag: Optional[str] = None   # "high" | "low" | "fallback"
