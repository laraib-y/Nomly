import logging
import re
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

# Next.js moves to 3001, 3002, and so on when 3000 is already taken.
LOCAL_ORIGIN = r"http://(localhost|127\.0\.0\.1):\d+"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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

    @app.middleware("http")
    async def reject_cross_site_writes(request: Request, call_next):
        """CSRF guard for the auth cookie: browser writes must come from a known origin."""
        if request.method in UNSAFE_METHODS and _needs_origin_check(request):
            origin = request.headers.get("origin")
            if origin is not None and not is_allowed_origin(origin):
                return JSONResponse(status_code=403, content={"detail": "Request origin is not allowed"})
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=LOCAL_ORIGIN,
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


def is_allowed_origin(origin: str) -> bool:
    return origin in get_settings().cors_origin_list or re.fullmatch(LOCAL_ORIGIN, origin) is not None


def _needs_origin_check(request: Request) -> bool:
    settings = get_settings()
    return request.url.path.startswith("/api/auth/") or settings.auth_cookie_name in request.cookies


app = create_app()
