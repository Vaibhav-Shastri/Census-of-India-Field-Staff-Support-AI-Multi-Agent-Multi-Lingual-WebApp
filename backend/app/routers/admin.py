# backend/app/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.routers.corrections import CORRECTIONS
from app.config.persona_loader import load_all_personas
import secrets
import os

router = APIRouter()
security = HTTPBasic()

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "yourStrongPassword")  # Set via env var in production!

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@router.get("/corrections", tags=["Admin"])
def get_corrections(admin: str = Depends(verify_admin)):
    return CORRECTIONS

@router.post("/persona_reload", tags=["Admin"])
def reload_personas(admin: str = Depends(verify_admin)):
    from app.config import persona_loader
    persona_loader.persona_prompts.clear()
    persona_loader.persona_prompts.update(load_all_personas())
    return {"message": "Personas reloaded"}
