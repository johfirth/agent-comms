from fastapi import FastAPI

from app.routers import agents, memberships, mentions, messages, threads, webhooks, work_items, workspaces

app = FastAPI(
    title="Agent Communication Server",
    description="A communication server for AI agents to collaborate in workspaces on software development.",
    version="0.1.0",
)

app.include_router(workspaces.router)
app.include_router(agents.router)
app.include_router(memberships.router)
app.include_router(threads.router)
app.include_router(messages.router)
app.include_router(mentions.router)
app.include_router(work_items.router)
app.include_router(webhooks.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
