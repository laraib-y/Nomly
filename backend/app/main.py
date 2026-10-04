import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import get_engine
from app.core.exceptions import AppError
from app.websocket.routes import router as websocket_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    engine = get_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    logger.info("Database connection ok")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DineOff API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        body: dict[str, str] = {"detail": exc.detail}
        if exc.code:
            body["code"] = exc.code
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"name": "DineOff", "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
