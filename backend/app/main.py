"""CostWise AI HTTP application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import Base, engine, ensure_expense_pert_columns
from app.limiter import limiter
from app.logging_config import logger
from app.routers import ai, analytics, auth, expenses, imports, pert, projects, reports, security_center
from app.services.audit import client_ip, write_audit


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        path = request.url.path
        # Swagger UI loads its own scripts. The JSON API keeps a strict policy.
        if path not in {"/docs", "/redoc", "/openapi.json"} and not path.startswith("/docs/"):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            settings = get_settings()
            limit = settings.max_upload_bytes if request.url.path.endswith("/imports/preview") else settings.max_json_bytes
            raw_length = request.headers.get("content-length")
            if raw_length and raw_length.isdigit() and int(raw_length) > limit:
                return JSONResponse(status_code=413, content={"detail": "Request is too large."})
        return await call_next(request)


def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.info("rate_limited path=%s", request.url.path)
    write_audit("rate_limited", ip_address=client_ip(request), detail=f"path={request.url.path}")
    response = JSONResponse(status_code=429, content={"detail": "Too many requests. Try again later."})
    response.headers["Retry-After"] = "60"
    return response


async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, RateLimitExceeded):
        return rate_limit_handler(request, exc)
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})
    logger.error("unhandled_error type=%s path=%s", type(exc).__name__, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.secret_key == "replace-with-a-long-random-string":
        logger.warning("Signing key is still the example placeholder. Set a unique value before any shared deployment.")
    Base.metadata.create_all(bind=engine)
    ensure_expense_pert_columns()
    from app.seed import fill_seeded_pert

    fill_seeded_pert()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(expenses.router)
    app.include_router(imports.router)
    app.include_router(analytics.router)
    app.include_router(pert.router)
    app.include_router(ai.router)
    app.include_router(reports.router)
    app.include_router(security_center.router)

    @app.get("/api/health", tags=["Health"])
    def health():
        return {"status": "ok", "app": settings.app_name, "ai_mode": settings.ai_mode}

    @app.get("/", include_in_schema=False)
    def home():
        app_url = "http://127.0.0.1:5173"
        for origin in settings.cors_origin_list:
            cleaned = origin.rstrip("/")
            if "127.0.0.1:5173" in cleaned:
                app_url = cleaned
                break
        return RedirectResponse(app_url, status_code=302)

    return app


app = create_app()
