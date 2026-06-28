# backend/app/routers/flavors.py

from fastapi import APIRouter
from app.config.persona_loader import get_assistant_flavors

router = APIRouter()

@router.get("/flavors", tags=["Flavors"])
async def flavors():
    return get_assistant_flavors()
