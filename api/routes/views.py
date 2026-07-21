from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..deps import get_current_active_user
from ..database.models import User

router = APIRouter(tags=["UI Views"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

TEMPLATES_DIR = PROJECT_ROOT / "frontend" / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/role")
async def get_user_role(current_user: User = Depends(get_current_active_user)):
    return {"role": current_user.role}

@router.get("/partials/{file_name}", response_class=HTMLResponse)
async def serve_partial_html(request: Request, file_name: str):
    return templates.TemplateResponse(f"partials/{file_name}", {"request": request})