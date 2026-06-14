from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import sentry_sdk

from ..deps import get_db, check_admin_access
from ..database.models import User
from ..database.schemas import (
    UserCreate, UserOut, UserUpdate, 
    TentCreate, TentOut, TentUpdate,
    CompanyUpdate, CompanyOut
)
from ..database.events import UserCRUD, TentCRUD, CompanyCRUD
from ..database.events.chat_events import InteractionCRUD
from backend.services.tenant_manager import MultiTenantDBManager
from backend.utils.responses import create_response
from api.config import settings

router = APIRouter(prefix="/api/admin", tags=["Company Administration"])

# --- COMPANY SETTINGS ---

@router.get("/company", response_model=CompanyOut)
async def get_my_company(
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    company = CompanyCRUD.get_by_id(db, current_user.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.patch("/company", response_model=CompanyOut)
async def update_my_company(
    request: CompanyUpdate,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Update company-wide settings (Theme, Graph Config, Metrics)."""
    return CompanyCRUD.update(db, current_user.company_id, request, actor_id=current_user.user_id)

# --- USER MANAGEMENT ---

@router.get("/users", response_model=List[UserOut])
async def list_company_users(
    current_user: User = Depends(check_admin_access), 
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=settings.ADMIN_PAGE_MAX_LIMIT, description="Max records to return"),
):
    return UserCRUD.get_all_by_company(db, current_user.company_id, skip=skip, limit=limit)

@router.post("/users", response_model=UserOut)
async def create_company_user(
    user_data: UserCreate, 
    current_user: User = Depends(check_admin_access), 
    db: Session = Depends(get_db)
):
    user_data.company_id = current_user.company_id
    try:
        return UserCRUD.create(db, user_data, actor_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/users/{user_id}", response_model=UserOut)
async def update_company_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    target_user = UserCRUD.get_by_id(db, user_id)
    if not target_user or target_user.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="User not found or access denied")
    return UserCRUD.update(db, user_id, user_data, actor_id=current_user.user_id)

@router.delete("/users/{user_id}")
async def delete_company_user(
    user_id: int, 
    current_user: User = Depends(check_admin_access), 
    db: Session = Depends(get_db)
):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Self-deletion is not permitted.")  
    target_user = UserCRUD.get_by_id(db, user_id)
    if not target_user or target_user.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="User not found or access denied.")  
    success = UserCRUD.delete(db, user_id, actor_id=current_user.user_id)
    return create_response(success, "User removed")

# --- TENT MANAGEMENT ---

@router.get("/tents", response_model=List[TentOut])
async def list_company_tents(
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=settings.ADMIN_PAGE_MAX_LIMIT, description="Max records to return"),
):
    return TentCRUD.get_tents_by_company(db, current_user.company_id, skip=skip, limit=limit)

@router.post("/tents", response_model=TentOut)
async def create_company_tent(
    request: TentCreate,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    request.company_id = current_user.company_id
    try:
        return await TentCRUD.create(db, request, actor_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.patch("/tents/{db_id}", response_model=TentOut)
async def update_company_tent(
    db_id: int,
    request: TentUpdate,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    tent = TentCRUD.get_by_id(db, db_id)
    if not tent or tent.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Database access denied.")
    if request.connection_config is not None:
        await MultiTenantDBManager.disconnect_tent(db_id)
    return TentCRUD.update(db, db_id, request, actor_id=current_user.user_id)

@router.get("/tents/{db_id}/schema")
async def get_tent_schema(
    db_id: int,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    tent = TentCRUD.get_by_id(db, db_id)
    if not tent or tent.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Database access denied.")
    result = await MultiTenantDBManager.get_schema_for_tent(tent)
    if not result["success"]:
        sentry_sdk.set_context("database", {"id": db_id, "type": tent.db_type})
        sentry_sdk.capture_message(f"Schema retrieval failed: {result['message']}", level="error")
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.delete("/tents/{db_id}")
async def delete_company_tent(
    db_id: int,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    tent = TentCRUD.get_by_id(db, db_id)
    if not tent or tent.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    success = await TentCRUD.delete(db, db_id, actor_id=current_user.user_id)
    return create_response(success, "Database connection removed.")

@router.post("/tents/test")
async def test_database_connection(
    request: TentCreate,
    current_user: User = Depends(check_admin_access)
):
    return MultiTenantDBManager.test_connection_with_config(
        request.db_type, request.connection_config
    )
    
# --- INTERACTION FEEDBACK ---

@router.post("/interactions/{interaction_id}/feedback")
async def submit_feedback(
    interaction_id: int,
    feedback: bool,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    result = InteractionCRUD.set_feedback(db, interaction_id, feedback)
    if not result:
        raise HTTPException(status_code=404, detail="Interaction not found.")
    return create_response(True, "Feedback recorded.")