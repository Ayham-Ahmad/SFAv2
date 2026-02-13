from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..deps import get_db, check_super_admin_access
from ..database.models import User
from ..database.schemas import CompanyOut, UserOut, UserUpdate
from ..database.events import CompanyCRUD, UserCRUD, InteractionCRUD
from backend.utils.responses import create_response
from ..constants import UserRole

router = APIRouter(prefix="/api/super-admin", tags=["Platform administration"])

@router.get("/companies", response_model=List[CompanyOut])
async def list_all_companies(
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db)
):
    return CompanyCRUD.get_all(db)

@router.get("/company-admins", response_model=List[UserOut])
async def list_company_admins(
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db)
):
    return UserCRUD.get_admins(db)

@router.patch("/admins/{user_id}", response_model=UserOut)
async def update_company_admin(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db)
):
    target_user = UserCRUD.get_by_id(db, user_id)
    if not target_user or target_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Company Admin not found")
    
    return UserCRUD.update(db, user_id, user_data, current_user.user_id)

@router.get("/usage/llm")
async def get_llm_usage_stats(
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db)
):
    return InteractionCRUD.get_llm_usage(db)

@router.delete("/companies/{company_id}")
async def offboard_company(
    company_id: int,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db)
):
    success = CompanyCRUD.delete(db, company_id)
    if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Company with ID {company_id} not found or could not be deleted."
            )
            
    return create_response(success, "Company and its admin successfully offboarded.")