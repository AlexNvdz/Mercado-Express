"""FastAPI application entrypoint.

Run in development with:
    uv run uvicorn app.main:app --reload
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.asyncio_compat import apply_windows_event_loop_policy
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    InsufficientStockError,
    InvalidStateTransitionError,
    NotFoundError,
    ValidationAppError,
)
from app.routers.v1.api import api_router

# Must happen before uvicorn's event loop starts (any time before serving
# begins is fine -- see app/core/asyncio_compat.py).
apply_windows_event_loop_policy()

configure_logging()
logger = logging.getLogger(__name__)

_ERROR_STATUS_MAP: dict[type[AppError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationAppError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InsufficientStockError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    InvalidStateTransitionError: status.HTTP_409_CONFLICT,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Starting %s (%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="MercadoExpress backend REST API.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _register_exception_handler(exc_class: type[AppError], http_status: int) -> None:
    @app.exception_handler(exc_class)
    async def _handler(request: Request, exc: AppError, _status: int = http_status) -> JSONResponse:
        logger.warning("%s: %s (%s %s)", exc_class.__name__, exc.detail, request.method, request.url.path)
        return JSONResponse(status_code=_status, content={"detail": exc.detail})


for exc_class, http_status in _ERROR_STATUS_MAP.items():
    _register_exception_handler(exc_class, http_status)


@app.exception_handler(AppError)
async def _fallback_app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.error("Unhandled AppError: %s", exc.detail)
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.detail})


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
