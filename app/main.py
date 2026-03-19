import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.database import engine
from app.routers import agents, dashboard, dashboard_page, memberships, mentions, messages, threads, webhooks, work_items, workspaces

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify critical tables exist after alembic migration."""
    required = ["agents", "workspaces", "memberships", "threads", "messages", "mentions", "work_items"]
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            existing = {row[0] for row in result}

        missing = [t for t in required if t not in existing]
        if missing:
            logger.error(
                "CRITICAL: Required tables missing after migration: %s. "
                "The database may need to be reset: docker compose down -v && docker compose up -d",
                missing,
            )
        else:
            logger.info("Database verified: all %d required tables present", len(required))
    except Exception:
        logger.warning("Could not verify database tables (database may not be PostgreSQL in test mode)")
    yield


app = FastAPI(
    title="Agent Communication Server",
    description="A communication server for AI agents to collaborate in workspaces on software development.",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Rate limiting (Issue #2) -----------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# --- Security headers (Issue #3) --------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database constraint violations with a clean 409 instead of leaking SQL."""
    logger.warning("Database integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=409,
        content={"detail": "Resource conflict: a unique constraint was violated"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle invalid enum values and other ValueErrors with 422 instead of 500."""
    logger.warning("Value error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content={"detail": f"Invalid value: {exc}"},
    )


app.include_router(workspaces.router)
app.include_router(dashboard_page.router)
app.include_router(agents.router)
app.include_router(dashboard.router)
app.include_router(memberships.router)
app.include_router(threads.router)
app.include_router(messages.router)
app.include_router(mentions.router)
app.include_router(work_items.router)
app.include_router(webhooks.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
