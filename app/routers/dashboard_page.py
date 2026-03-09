from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter(tags=["dashboard"])

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@router.get("/dashboard")
async def dashboard_page():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))
