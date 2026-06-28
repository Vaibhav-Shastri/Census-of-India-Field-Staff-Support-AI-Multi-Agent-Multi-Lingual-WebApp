# backend/app/models/session.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Session(BaseModel):
    uuid: str
    user_name: str
    language: str
    style: str         # Style/flavor directly tracked
    last_topic: str
    history: List[Dict[str, Any]]
    flags: Dict[str, Any] = Field(default_factory=dict)
