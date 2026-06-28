# backend/app/routers/corrections.py

from fastapi import APIRouter
from app.models.corrections import CorrectionEvent
from uuid import uuid4
from datetime import datetime
from typing import List

router = APIRouter()
CORRECTIONS: List[CorrectionEvent] = []

@router.post("/correction", tags=["Corrections"])
async def submit_correction(event: CorrectionEvent):
    event.event_id = uuid4()
    event.status = "pending"
    event.reviewed_at = None
    CORRECTIONS.append(event)
    return {"message": "Correction submitted and pending review."}

@router.get("/corrections", tags=["Corrections"])
async def list_corrections():
    return CORRECTIONS


from fastapi import HTTPException

@router.post("/correction/{event_id}/review", tags=["Corrections"])
async def review_correction(event_id: str, approve: bool, reviewer: str = "admin"):
    for corr in CORRECTIONS:
        if str(corr.event_id) == event_id:
            if approve:
                corr.status = "approved"
            else:
                corr.status = "rejected"
            corr.reviewer = reviewer
            corr.reviewed_at = datetime.utcnow()
            return {"message": f"Correction {corr.status}."}
    raise HTTPException(status_code=404, detail="Correction not found")
