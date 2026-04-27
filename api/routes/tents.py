from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import sentry_sdk

from backend.services.tenant_manager import MultiTenantDBManager
from ..deps import get_db, get_current_active_user, check_admin_access, check_super_admin_access
from ..database.models import User
from ..database.schemas import TentCreate, TentOut, TentUpdate, CompanySummaryOut, DatabaseQueryRequest
from ..database.events import TentCRUD, CompanyCRUD
from ..constants import UserRole

router = APIRouter(prefix="/api/tents", tags=["Database Tents"])

@router.get("/types")
async def get_database_types():
    return {
        "types": MultiTenantDBManager.get_supported_types()
    }

@router.post("/test")
async def test_connection(
    request: TentCreate,
    current_user: User = Depends(check_admin_access)
):
    return MultiTenantDBManager.test_connection_with_config(
        request.db_type,
        request.connection_config
    )

@router.post("/", response_model=TentOut)
async def create_tent(
    request: TentCreate,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    request.company_id = current_user.company_id
 
    try:
        return TentCRUD.create(db, request, actor_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/", response_model=List[TentOut])
async def list_tents(
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    return TentCRUD.get_tents_by_company(db, current_user.company_id)

@router.get("/summary", response_model=List[CompanySummaryOut])
async def get_global_tent_summary(
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db)
):
    return CompanyCRUD.get_companies_summary(db)

@router.get("/{db_id}/schema")
async def get_tent_schema(
    db_id: int,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    tent = TentCRUD.get_by_id(db, db_id)
    if not tent:
        raise HTTPException(status_code=404, detail="Database not found")
    
    if tent.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this database")
    
    result = MultiTenantDBManager.get_schema_for_tent(tent)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.patch("/{db_id}", response_model=TentOut)
async def update_tent(
    db_id: int,
    request: TentUpdate,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    tent = TentCRUD.get_by_id(db, db_id)
    if not tent:
        raise HTTPException(status_code=404, detail="Database not found")
        
    if tent.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this database")

    if request.connection_config is not None:
        MultiTenantDBManager.disconnect_tent(db_id)

    return TentCRUD.update(db, db_id, request, actor_id=current_user.user_id)

@router.post("/query")
async def execute_query(
    request: DatabaseQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    tent = TentCRUD.get_by_id(db, request.db_id)
    if not tent:
        raise HTTPException(status_code=404, detail="Database not found")
        
    if current_user.role == UserRole.SUPERADMIN and tent.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to query this database")

    result = MultiTenantDBManager.execute_query_for_tent(tent, request.query)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("message", "Query failed"))
    return result

@router.delete("/{db_id}")
async def delete_tent(
    db_id: int,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    tent = TentCRUD.get_by_id(db, db_id)
    if not tent:
        raise HTTPException(status_code=404, detail="Database not found")
        
    if tent.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this database")
        
    success = TentCRUD.delete(db, db_id, actor_id=current_user.user_id)
    return {"success": success, "message": "Database connection removed"}