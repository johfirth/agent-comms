import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.routers import agents, dashboard, dashboard_page, memberships, mentions, messages, threads, webhooks, work_items, workspaces

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agent Communication Server",
    description="A communication server for AI agents to collaborate in workspaces on software development.",
    version="0.1.0",
)


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
