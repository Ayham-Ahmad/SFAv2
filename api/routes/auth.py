from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from fastapi import Response

from ..deps import get_db, get_current_active_user
from ..database.events import UserCRUD, SessionCRUD, CompanyCRUD
from ..database.models import User
from ..database.schemas import UserCreate, UserOut, CompanyCreate, RegisterRequest, RegisterResponse
from ..security import (
    verify_password,
    create_access_token, get_access_token_expires,
    generate_reset_token, get_reset_token_expires,
)
from backend.services.email_service import send_password_reset_email, send_welcome_email

router = APIRouter(tags=["Authentication"])

# ── Login (root /token for OAuth2PasswordRequestForm compatibility) ───────────

@router.post("/token")
async def login(
    response: Response,
    creds: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)):
    user = UserCRUD.get_by_username(db, creds.username)
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive.")

    UserCRUD.update_last_login(db, user)
    session = SessionCRUD.create(db, user.user_id)
    token   = create_access_token(
        data={"sub": user.username, "company_id": user.company_id, "role": user.role},
        access_token_expires=get_access_token_expires(),
    )
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,   # True in production with HTTPS later
        samesite="lax",
        max_age=60 * 60
    )
    
    company = CompanyCRUD.get_by_id(db, user.company_id) if user.company_id else None
    return {"session_id": session.session_id,
            "user": {"user_id": user.user_id, "username": user.username, "email": user.email,
                     "company_id": user.company_id, "company_name": company.company_name if company else None,
                     "role": user.role}}

# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = SessionCRUD.get_active_by_user(db, current_user.user_id)
    if session:
        SessionCRUD.end_session(db, session.session_id)
    return {"success": True, "message": "Logged out."}

# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/api/auth/register", response_model=RegisterResponse, status_code=201)
async def register(payload: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if UserCRUD.get_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username already taken.")
    if UserCRUD.get_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    if CompanyCRUD.get_by_name(db, payload.company_name):
        raise HTTPException(status_code=400, detail="Company already registered.")

    new_company = CompanyCreate(company_name=payload.company_name)
    new_user = UserCreate(username=payload.username, email=payload.email,
                          password=payload.password)
    try:
        company = CompanyCRUD.create(db, new_company, new_user, 1)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    background_tasks.add_task(send_welcome_email, new_user.email, new_user.username)
    return RegisterResponse(success=True)

# ── Forgot password ───────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/api/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = UserCRUD.get_by_email(db, payload.email)
    if user:
        token  = generate_reset_token()
        expire = get_reset_token_expires()
        UserCRUD.set_password_reset_token(db, user, token, expire)
        background_tasks.add_task(send_password_reset_email, user.email, user.username, token)
    return {"success": True, "message": "If that email is registered, a reset link has been sent."}

# ── Reset password ────────────────────────────────────────────────────────────

class ResetPasswordRequest(BaseModel):
    token: str; new_password: str

@router.post("/api/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = UserCRUD.get_by_reset_token(db, payload.token)
    if not user or not UserCRUD.is_reset_token_valid(user, payload.token):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    UserCRUD.update(db, user.user_id, {"password": payload.new_password}, actor_id=user.user_id)
    UserCRUD.clear_reset_token(db, user)
    return {"success": True, "message": "Password reset successfully."}

# ── Change password (authenticated) ──────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str; new_password: str

@router.post("/api/auth/change-password")
async def change_password(payload: ChangePasswordRequest,
                          current_user: User = Depends(get_current_active_user),
                          db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    UserCRUD.update(db, current_user.user_id, {"password": payload.new_password}, actor_id=current_user.user_id)
    return {"success": True, "message": "Password changed."}
