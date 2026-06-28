# backend/app/models/message.py

from datetime import datetime
from pydantic import BaseModel

class ChatMessage(BaseModel):
    persona: str
    content: str
    timestamp: datetime
    language: str
    typing_indicator: bool = False
