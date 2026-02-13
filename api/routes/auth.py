from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..deps import get_db
from ..database.events import UserCRUD
from ..security import verify_password, create_access_token, get_access_token_expires

router = APIRouter(tags=["Authentication"])

@router.post("/token")
async def login_for_access_token(
    creds: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = UserCRUD.get_by_username(db, creds.username)

    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    UserCRUD.update_last_login(db, user)

    token_payload = {
        "sub": user.username,
        "company_id": user.company_id,
        "role": user.role
    }

    token = create_access_token(
        data=token_payload, access_token_expires=get_access_token_expires()
    )

    return {
        "access_token": token, 
        "token_type": "bearer", 
        "user": {
            "username": user.username,
            "company_id": user.company_id,
            "role": user.role
        }
    }