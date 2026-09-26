"""FastAPI Application Factory for invst."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from invst.api.routes import router as api_router
from invst.api.mf_routes import router as mf_router
from invst.config import get_project_root


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Arth IQ API",
        description="Arth IQ — Your Personal Investment Intelligence Engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration for frontend dev servers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register global exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        error_msgs = []
        for err in errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []) if l != "body")
            msg = err.get("msg", "Invalid value")
            error_msgs.append(f"{loc}: {msg}" if loc else msg)
        detail = "; ".join(error_msgs) if error_msgs else "Validation failed for request data."
        return JSONResponse(
            status_code=422,
            content={"detail": detail, "error_type": "ValidationError", "errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail, "status_code": exc.status_code, "error_type": "HTTPException"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger = logging.getLogger("invst.api")
        logger.exception("Unhandled server exception at %s %s: %s", request.method, request.url.path, exc)
        exc_name = type(exc).__name__
        exc_msg = str(exc).strip()
        if "operationalerror" in exc_name.lower() or "database" in exc_name.lower():
            detail = f"Database operation error: {exc_msg or 'Failed to execute query.'}"
        elif "connection" in exc_name.lower():
            detail = f"Connection error: {exc_msg or 'Service is temporarily unreachable.'}"
        elif exc_msg:
            detail = f"Server error ({exc_name}): {exc_msg}"
        else:
            detail = f"Internal server error ({exc_name}). Please try again."

        return JSONResponse(
            status_code=500,
            content={"detail": detail, "error_type": exc_name},
        )

    # Register API routes
    app.include_router(api_router)
    app.include_router(mf_router, prefix="/api")

    # Mount pre-built React frontend if dist/ exists
    root = get_project_root()
    dist_dir = root / "frontend" / "dist"
    if not dist_dir.is_dir():
        dist_dir = root.parent / "frontend" / "dist"
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")

    return app


app = create_app()
