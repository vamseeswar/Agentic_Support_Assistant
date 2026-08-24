from fastapi import APIRouter, Query, HTTPException
from app.services.policy_service import policy_service
from app.models import PolicySearchResult

router = APIRouter(prefix="/api/policy", tags=["Policy"])

@router.get("/search", response_model=PolicySearchResult)
async def search_policy_endpoint(q: str = Query(..., description="Query terms to search in policy document")):
    """Search policy document with lexical scoring and section citations."""
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    return policy_service.search(q, top_k=3)

@router.get("/raw")
async def get_raw_policy():
    """Retrieve raw markdown of the full policy document."""
    return {"content": policy_service.get_full_text()}
