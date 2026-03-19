from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
import os

from app.services.auth import optional_auth

router = APIRouter(tags=["dashboard"])

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@router.get("/dashboard")
async def dashboard_page(_auth=Depends(optional_auth)):
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))
