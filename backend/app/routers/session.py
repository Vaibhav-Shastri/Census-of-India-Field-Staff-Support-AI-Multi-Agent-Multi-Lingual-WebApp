# backend/app/routers/session.py

from fastapi import APIRouter
from app.models.session import Session
from uuid import uuid4
from app.session_store import SESSION_STORE

router = APIRouter()

@router.post("/session", tags=["Session"])
async def create_session(user_name: str = "User", language: str = "en", style: str = "friendly"):
    session_id = str(uuid4())
    session = Session(
        uuid=session_id,
        user_name=user_name,
        language=language,
        style=style,
        last_topic="",
        history=[],
        flags={"previous_language": language, "previous_style": style}
    )
    SESSION_STORE[session_id] = session
    return {"session_id": session_id, "session": session}

@router.get("/session/{session_id}", tags=["Session"])
async def get_session(session_id: str):
    session = SESSION_STORE.get(session_id)
    if not session:
        return {"error": "Session not found"}
    return {"session_id": session_id, "session": session}
