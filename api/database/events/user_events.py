from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Union, Optional, List
from pydantic import BaseModel

from ..models import User
from .modify_events import record_modification, get_current_snapshot
from ...constants import TableName, ActionType, PLAN_LIMITS, CompanyPlan, UserRole
from ...utils import to_dict
from ...security import get_password_hash

class UserCRUD:
    @staticmethod
    def create(db: Session, user_data: Union[dict, BaseModel], actor_id: Optional[int] = None) -> User:
        from .company_events import CompanyCRUD # Lazy Import
        
        data = to_dict(user_data)

        if "password" in data:
            plain_password = data.pop("password")
            data["hashed_password"] = get_password_hash(plain_password)
    
        if data.get("company_id"):
            company = CompanyCRUD.get_by_id(db, data["company_id"])
            if company:
                limit = PLAN_LIMITS.get(company.plan, PLAN_LIMITS[CompanyPlan.FREE])["managers"]
                if company.managers_count >= limit:
                    raise ValueError(f"Manager limit reached for {company.plan} plan ({limit}).")

        new_user = User(**data)
        db.add(new_user)            
        db.flush()

        if new_user.company_id:
            company = CompanyCRUD.get_by_id(db, new_user.company_id)
            if company:
                company_old_snapshot = get_current_snapshot(company)
                company.managers_count += 1
                record_modification(db, TableName.COMPANIES, company.company_id, ActionType.UPDATE, actor_id, company_old_snapshot)

        record_modification(db, TableName.USERS, new_user.user_id, ActionType.CREATE, actor_id, None)

        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.user_id == user_id).first()
    
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_all(db: Session) -> List[User]:
        return db.query(User).order_by(User.username).all()

    @staticmethod
    def get_all_by_company(db: Session, company_id: int) -> List[User]: 
        return db.query(User).filter(User.company_id == company_id).order_by(User.user_created_at.desc()).all()
    
    @staticmethod
    def get_admins(db: Session):
        return db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.user_id).all()
    
    @staticmethod
    def update_last_login(db: Session, user: User):
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

    @staticmethod
    def set_password_reset_token(db: Session, user: User, token: str, expire: datetime):
        user.reset_token = token
        user.reset_token_expires = expire
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def is_reset_token_valid(user: User, token: str) -> bool:
        if user.reset_token != token:
            return False
        if not user.reset_token_expires or datetime.now(timezone.utc) > user.reset_token_expires:
            return False
        return True

    @staticmethod
    def update(db: Session, user_id: int, updated_data: Union[dict, BaseModel], actor_id: Optional[int] = None) -> Optional[User]:
        user_record = UserCRUD.get_by_id(db, user_id)
        if user_record:
            snapshot_before_update = get_current_snapshot(user_record)
            data = to_dict(updated_data, for_update=True)

            for key, value in data.items():
                if hasattr(user_record, key):
                    setattr(user_record, key, value)
            
            record_modification(db, TableName.USERS, user_id, ActionType.UPDATE, actor_id, snapshot_before_update)

            db.commit()
            db.refresh(user_record)
        return user_record

    @staticmethod
    def delete(db: Session, user_id: int, actor_id: Optional[int] = None) -> bool:
        from .company_events import CompanyCRUD # Lazy Import

        user_record = UserCRUD.get_by_id(db, user_id)
        if user_record:
            last_snapshot_before_delete = get_current_snapshot(user_record)
            
            if user_record.company_id: 
                company = CompanyCRUD.get_by_id(db, user_record.company_id)
                if company:
                    company_old_snapshot = get_current_snapshot(company)
                    company.managers_count -= 1
                    record_modification(db, TableName.COMPANIES, company.company_id, ActionType.UPDATE, actor_id, company_old_snapshot)

            record_modification(db, TableName.USERS, user_id, ActionType.DELETE, actor_id, last_snapshot_before_delete)
            
            db.delete(user_record)
            db.commit()
            return True
        return False