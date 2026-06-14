from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_active_user
from ..database.models import User
from ..database.schemas import UserOut, UserUpdate
from ..database.events import UserCRUD

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    allowed_fields = {"username", "email", "ui_prefs"}
    filtered = {k: v for k, v in updates.model_dump(exclude_unset=True).items() if k in allowed_fields}
    updated = UserCRUD.update(db, current_user.user_id, filtered, actor_id=current_user.user_id)
    return updated
