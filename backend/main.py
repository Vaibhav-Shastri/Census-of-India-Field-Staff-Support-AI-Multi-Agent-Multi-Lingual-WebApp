# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.routers import chat, corrections, session, flavors, persona, admin

# Static serving
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="CensusDas.AI Staff Room Backend", version="0.1.0")

# CORS is not needed when frontend is same origin; keep permissive during initial test.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API routes (must be added BEFORE the static mount) ---
app.include_router(chat.router, prefix="/api")
app.include_router(corrections.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(flavors.router, prefix="/api")
app.include_router(persona.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# --- Serve the built frontend (Vite dist/) ---
DIST_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "dist"))

if os.path.isdir(DIST_DIR):
    # Serve all files under / (e.g., /assets/*)
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="spa")

    # SPA fallback so client-side routes work (e.g., /settings)
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
else:

    @app.get("/")
    async def root():
        return {
            "ok":
            True,
            "message":
            "Front-end build not found. Run `npm run build` at repo root."
        }
