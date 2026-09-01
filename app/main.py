import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.patients import router as patients_router
from app.api.voice_tools import router as voice_tools_router
from app.config import get_settings
from app.db.session import check_database_connection, get_db
from app.observability import (
    REQUEST_ID_HEADER,
    configure_logging,
    end_request_trace,
    start_request_trace,
)
from app.schemas.response import ApiResponse, ErrorDetail

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize resources needed by the API process."""
    check_database_connection()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for voice-based patient registration.",
    lifespan=lifespan,
)
app.include_router(patients_router)
app.include_router(voice_tools_router)


@app.middleware("http")
async def trace_request(request: Request, call_next):
    request_id, token = start_request_trace(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    started_at = perf_counter()
    logger.info("Request started method=%s path=%s", request.method, request.url.path)

    try:
        response = await call_next(request)
        duration_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "Request completed method=%s path=%s status_code=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    except Exception:
        duration_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "Unhandled request failure method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    finally:
        end_request_trace(token)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    logger.warning(
        "HTTP request rejected method=%s path=%s status_code=%s",
        request.method,
        request.url.path,
        exc.status_code,
    )
    content = ApiResponse[None](error=ErrorDetail(message=message)).model_dump()
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "Request validation failed method=%s path=%s error_count=%s",
        request.method,
        request.url.path,
        len(exc.errors()),
    )
    content = ApiResponse[None](
        error=ErrorDetail(message="Request validation failed")
    ).model_dump()
    return JSONResponse(status_code=422, content=content)


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(
        "Database request failed method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    content = ApiResponse[None](
        error=ErrorDetail(message="Database operation failed")
    ).model_dump()
    return JSONResponse(status_code=500, content=content)


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unexpected request failure method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    content = ApiResponse[None](
        error=ErrorDetail(message="Internal server error")
    ).model_dump()
    return JSONResponse(status_code=500, content=content)


@app.get("/health", tags=["system"], response_model=ApiResponse[dict[str, str]])
def health_check(
    session: Annotated[Session, Depends(get_db)],
) -> ApiResponse[dict[str, str]]:
    """Report whether the API and its database connection are ready."""
    session.execute(text("SELECT 1"))
    return ApiResponse(data={"status": "ok"})
