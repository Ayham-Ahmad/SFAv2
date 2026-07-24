from sqlalchemy.orm import Session
from typing import Union, Optional, List
from pydantic import BaseModel

from ..models import User, Company, TentDatabase
from .modify_events import record_modification, get_current_snapshot
from ...constants import TableName, ActionType, UserRole
from ...utils import to_dict


class CompanyCRUD:
    @staticmethod
    def create(
        db: Session,
        company_data: Union[dict, BaseModel],
        admin_data: Union[dict, BaseModel],
        actor_id: int,
    ) -> Company:
        from . import UserCRUD  # Lazy import

        c_data = to_dict(company_data)
        a_data = to_dict(admin_data)

        new_company = Company(**c_data)
        db.add(new_company)
        db.flush()

        a_data["company_id"] = new_company.company_id
        a_data["role"] = UserRole.ADMIN

        UserCRUD.create(db, a_data, actor_id=actor_id)

        record_modification(
            db,
            TableName.COMPANIES,
            new_company.company_id,
            ActionType.CREATE,
            actor_id,
            None,
        )

        db.commit()
        db.refresh(new_company)
        return new_company

    @staticmethod
    def get_by_id(db: Session, company_id: int) -> Optional[Company]:
        return db.query(Company).filter(Company.company_id == company_id).first()

    @staticmethod
    def get_by_name(db: Session, company_name: str):
        return db.query(Company).filter(Company.company_name == company_name).first()

    @staticmethod
    def get_all(db: Session) -> List[Company]:
        return db.query(Company).order_by(Company.company_id).all()

    @staticmethod
    def get_companies_summary(db: Session):
        return db.query(
            Company.company_id,
            Company.company_name,
            Company.plan,
            Company.managers_count,
            Company.databases_count,
            Company.company_created_at,
        ).all()

    @staticmethod
    def update(
        db: Session, company_id: int, updated_data: Union[dict, BaseModel], actor_id
    ) -> Optional[Company]:
        company_record = CompanyCRUD.get_by_id(db, company_id)
        if company_record:
            company_old_snapshot = get_current_snapshot(company_record)

            data = to_dict(updated_data, for_update=True)

            for key, value in data.items():
                if hasattr(company_record, key):
                    setattr(company_record, key, value)

            record_modification(
                db,
                TableName.COMPANIES,
                company_id,
                ActionType.UPDATE,
                actor_id,
                company_old_snapshot,
            )
            db.commit()
            db.refresh(company_record)
        return company_record

    @staticmethod
    def _delete_all_company_users(db: Session, company_id: int, actor_id: int):
        from .user_events import UserCRUD  # Lazy Import

        users = db.query(User).filter(User.company_id == company_id).all()
        for user in users:
            UserCRUD.delete(db, user.user_id, actor_id)

    @staticmethod
    def _delete_all_company_tents(db: Session, company_id: int, actor_id: int):
        from .tent_events import TentCRUD  # Lazy Import

        tents = (
            db.query(TentDatabase).filter(TentDatabase.company_id == company_id).all()
        )
        for tent in tents:
            TentCRUD.delete(db, tent.db_id, actor_id)

    @staticmethod
    def delete(db: Session, company_id: int, actor_id) -> bool:
        company_record = (
            db.query(Company).filter(Company.company_id == company_id).first()
        )
        if company_record:
            CompanyCRUD._delete_all_company_users(db, company_id, actor_id)
            CompanyCRUD._delete_all_company_tents(db, company_id, actor_id)

            record_modification(
                db,
                TableName.COMPANIES,
                company_id,
                ActionType.DELETE,
                actor_id,
                get_current_snapshot(company_record),
            )
            db.delete(company_record)
            db.commit()
            return True
        return False
