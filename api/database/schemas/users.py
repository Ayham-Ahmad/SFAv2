from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from ...constants import UserRole, ThemesTypes, Languages
from .base import BaseSchema

class UserPreferences(BaseModel):
    theme: ThemesTypes = ThemesTypes.AUTO
    language: Languages = Languages.ENGLISH

class UserBase(BaseSchema):
    username: str
    email: EmailStr
    role: Optional[UserRole] = None
    company_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    ui_prefs: Optional[UserPreferences] = None

class UserOut(UserBase):
    user_id: int
    is_active: bool
    user_created_at: datetime
    last_login: Optional[datetime] = None
    ui_prefs: UserPreferences = Field(default_factory=UserPreferences)