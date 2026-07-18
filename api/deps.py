from fastapi import Depends, HTTPException, status, Cookie
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .database.schemas import TokenData
from .database.database import SessionLocal
from .database.models import User
from .database.events import UserCRUD
from .config import settings
from .constants import UserRole

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
async def get_token_from_cookie(
    access_token: str | None = Cookie(default=None)
):    
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    return access_token

async def get_current_user(
    db: Session = Depends(get_db),
    token: str  = Depends(get_token_from_cookie),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise exc
        token_data = TokenData(username=username)
    except JWTError:
        raise exc

    user = UserCRUD.get_by_username(db, token_data.username)
    if not user:
        raise exc
    return user

async def get_current_active_user(current_user: User= Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def check_super_admin_access(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Special access required.")
    return current_user

async def check_admin_access(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role not in (UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Special access required.")
    return current_user