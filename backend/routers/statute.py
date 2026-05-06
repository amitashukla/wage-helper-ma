"""Router: statute citation search.

GET /api/statute/search?q=<query>&top_k=5
"""

from fastapi import APIRouter, HTTPException, Query

from backend.services import statute_search

router = APIRouter(prefix="/statute", tags=["statute"])


@router.get("/search")
def statute_search_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(default=5, ge=1, le=20, description="Maximum results to return"),
):
    """Return statute and publication chunks most relevant to the query."""
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' must not be empty.")

    results = statute_search.search(query=q, top_k=top_k)
    return {"query": q, "results": results}
