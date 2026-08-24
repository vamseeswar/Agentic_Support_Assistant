from fastapi import APIRouter, HTTPException, Path
from typing import List
from app.services.escalation_service import escalation_service
from app.models import EscalationPayload

router = APIRouter(prefix="/api/escalations", tags=["Escalations"])

@router.get("", response_model=List[EscalationPayload])
async def list_escalations():
    """List all escalated human support tickets."""
    return escalation_service.get_all_escalations()

@router.get("/{escalation_id}", response_model=EscalationPayload)
async def get_escalation(escalation_id: str = Path(..., description="Escalation ticket ID (e.g., ESC-XXXXXX)")):
    """Get structured details of a specific escalation ticket."""
    esc = escalation_service.get_escalation(escalation_id)
    if not esc:
        raise HTTPException(status_code=404, detail=f"Escalation ticket '{escalation_id}' not found.")
    return esc
