from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Union, Optional

from ..models import Session as SessionModel, User
from ...utils import to_dict

class SessionCRUD:
    @staticmethod
    def create(db: Session, user_id: int):

        # first we make sure that there is not active session for this user
        db.query(SessionModel).filter(
            SessionModel.user_id == user_id,
            SessionModel.is_active == True
        ).update({
            SessionModel.is_active: False,
            SessionModel.session_ended_at: datetime.now(timezone.utc)
        })

        new_session = SessionModel(user_id=user_id)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session

    @staticmethod
    def get_by_company_id(db: Session, company_id: int):
        return db.query(SessionModel)\
            .join(SessionModel.user_session)\
            .filter(User.company_id == company_id)\
            .all()

    @staticmethod
    def get_active_by_user(db: Session, user_id: int) -> Optional[SessionModel]:
        return db.query(SessionModel).filter(
            SessionModel.user_id == user_id, 
            SessionModel.is_active == True
        ).first()

    @staticmethod
    def update(db: Session, session_id: int, updated_data: Union[dict, BaseModel]):
        session_record = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if session_record:
            data = to_dict(updated_data, for_update=True)
            for key, value in data.items():
                if hasattr(session_record, key):
                    setattr(session_record, key, value)
            db.commit()
            db.refresh(session_record)
        return session_record

    @staticmethod
    def end_session(db: Session, session_id: int):
        return SessionCRUD.update(db, session_id, {
            "is_active": False,
            "session_ended_at": datetime.now(timezone.utc)
        })