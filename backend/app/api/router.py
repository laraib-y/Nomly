from fastapi import APIRouter

from app.api.routes import auth, health, history, sessions, voice

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
