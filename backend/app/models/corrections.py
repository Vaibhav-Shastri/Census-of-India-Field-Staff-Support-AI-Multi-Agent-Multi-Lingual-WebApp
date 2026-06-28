# backend/app/models/corrections.py

from pydantic import BaseModel
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class CorrectionEvent(BaseModel):
    event_id: Optional[UUID] = None
    user_feedback: str
    expert_answer: str
    context: Dict[str, Any]
    status: str = "pending"
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
