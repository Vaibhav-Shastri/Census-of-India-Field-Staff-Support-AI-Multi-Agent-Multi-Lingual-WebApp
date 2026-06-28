# backend/app/routers/chat.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.models.session import Session
from app.session_store import SESSION_STORE
from app.orchestrator.conversation import handle_user_message
from app.config.persona_loader import get_assistant_greeting

router = APIRouter()

class UserMessage(BaseModel):
    message: str
    user_name: str = "User"
    language: str = "en"
    style: str = "friendly"
    session_id: Optional[str] = None

class PersonaReply(BaseModel):
    persona: str
    content: str
    timestamp: str
    language: str

@router.post("/chat", response_model=List[PersonaReply], tags=["Chat"])
async def chat_endpoint(msg: UserMessage):
    session = SESSION_STORE.get(msg.session_id) if msg.session_id else None
    is_new_session = False
    reintro_needed = False

    if not session:
        session = Session(
            uuid=msg.session_id or "unknown",
            user_name=msg.user_name,
            language=msg.language,
            style=msg.style,
            last_topic="",
            history=[],
            flags={"previous_language": msg.language, "previous_style": msg.style}
        )
        SESSION_STORE[msg.session_id] = session
        is_new_session = True
    else:
        # Detect language/style change mid-session for re-intro
        if (session.language != msg.language) or (session.style != msg.style):
            reintro_needed = True

    # Always update session with latest
    session.language = msg.language
    session.style = msg.style
    session.user_name = msg.user_name
    session.history.append({
        "persona": "User",
        "message": msg.message,
        "language": msg.language,
        "style": msg.style,
        "user_name": msg.user_name,
    })

    replies = []
    # If new session or reintro needed, Assistant greets again!
    if is_new_session or reintro_needed:
        greet = get_assistant_greeting(msg.language, msg.style)
        from datetime import datetime
        replies.append({
            "persona": "Assistant",
            "content": greet,
            "timestamp": datetime.utcnow().isoformat(),
            "language": msg.language
        })

    # Main conversation logic
    core_replies = await handle_user_message(msg.message, session)
    for reply in core_replies:
        session.history.append(reply)
    replies.extend(core_replies)
    return replies
