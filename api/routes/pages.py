from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="frontend/templates")


def _page(request: Request, template: str, **ctx):
    return templates.TemplateResponse(template, {"request": request, **ctx})


# ── Public ────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return _page(request, "login.html")

@router.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login")


# ── Shared (all authenticated roles) ─────────────────────────────────────────

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    return _page(request, "analytics.html")

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return _page(request, "profile.html")


# ── Admin ─────────────────────────────────────────────────────────────────────

@router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    return _page(request, "admin/settings.html")

@router.get("/admin/tents", response_class=HTMLResponse)
async def admin_tents(request: Request):
    return _page(request, "admin/tents.html")

@router.get("/admin/team", response_class=HTMLResponse)
async def admin_team(request: Request):
    return _page(request, "admin/team.html")


# ── Super admin ───────────────────────────────────────────────────────────────

@router.get("/super-admin/dashboard", response_class=HTMLResponse)
async def super_dashboard(request: Request):
    return _page(request, "super_admin/dashboard.html")

@router.get("/super-admin/companies", response_class=HTMLResponse)
async def super_companies(request: Request):
    return _page(request, "super_admin/companies.html")

@router.get("/super-admin/users", response_class=HTMLResponse)
async def super_users(request: Request):
    return _page(request, "super_admin/users.html")

@router.get("/super-admin/usage", response_class=HTMLResponse)
async def super_usage(request: Request):
    return _page(request, "super_admin/usage.html")
