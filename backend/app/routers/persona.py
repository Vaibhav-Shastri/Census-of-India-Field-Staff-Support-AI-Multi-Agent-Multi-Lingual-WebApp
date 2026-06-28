# backend/app/routers/persona.py

from fastapi import APIRouter
from app.config.persona_loader import load_all_personas

router = APIRouter()

@router.post("/persona_reload", tags=["Persona"])
def reload_personas():
    from app.config import persona_loader
    persona_loader.persona_prompts.clear()
    persona_loader.persona_prompts.update(load_all_personas())
    return {"status": "ok", "msg": "Personas reloaded!"}
