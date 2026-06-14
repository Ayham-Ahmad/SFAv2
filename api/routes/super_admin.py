from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List

from ..deps import get_db, check_super_admin_access
from ..database.models import User
from ..database.schemas import CompanyOut, UserOut, UserUpdate, CompanyCreate as CC, OnboardRequest
from ..database.events import CompanyCRUD, UserCRUD, InteractionCRUD
from backend.utils.responses import create_response
from ..constants import UserRole

router = APIRouter(prefix="/api/super-admin", tags=["Platform Administration"])


# ── Companies ─────────────────────────────────────────────────────────────────

@router.get("/companies", response_model=List[CompanyOut])
async def list_all_companies(
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    return CompanyCRUD.get_all(db)


@router.get("/companies/{company_id}", response_model=CompanyOut)
async def get_company(
    company_id: int,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    company = CompanyCRUD.get_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return company


@router.post("/companies", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def onboard_company(
    payload: OnboardRequest,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    if CompanyCRUD.get_by_name(db, payload.company_name):
        raise HTTPException(status_code=400, detail="Company name already exists.")
    if UserCRUD.get_by_username(db, payload.admin_username):
        raise HTTPException(status_code=400, detail="Admin username already taken.")
    if UserCRUD.get_by_email(db, payload.admin_email):
        raise HTTPException(status_code=400, detail="Admin email already registered.")

    company = CompanyCRUD.create(
        db,
        company_data=CC(company_name=payload.company_name, plan=payload.plan),
        admin_data={
            "username": payload.admin_username,
            "email":    payload.admin_email,
            "password": payload.admin_password,
            "role":     UserRole.ADMIN,
        },
        actor_id=current_user.user_id,
    )
    return company


@router.delete("/companies/{company_id}")
async def offboard_company(
    company_id: int,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    success = CompanyCRUD.delete(db, company_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found.")
    return create_response(True, "Company and admin successfully offboarded.")


# ── Admins ────────────────────────────────────────────────────────────────────

@router.get("/company-admins", response_model=List[UserOut])
async def list_company_admins(
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    return UserCRUD.get_admins(db)


@router.patch("/admins/{user_id}", response_model=UserOut)
async def update_company_admin(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    target = UserCRUD.get_by_id(db, user_id)
    if not target or target.role != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Company Admin not found.")
    return UserCRUD.update(db, user_id, user_data, current_user.user_id)


# ── Usage stats ───────────────────────────────────────────────────────────────

@router.get("/usage/llm")
async def get_llm_usage_stats(
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    return InteractionCRUD.get_llm_usage(db)