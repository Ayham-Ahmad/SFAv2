from fastapi import APIRouter, Depends

from ..deps import get_current_active_user
from ..database.models import User
from ..database.schemas import UserOut

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user