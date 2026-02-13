from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Union, Optional, List, Dict
from pydantic import BaseModel

from ..models import TentDatabase, Company
from .modify_events import record_modification, get_current_snapshot
from ...constants import TableName, ActionType, PLAN_LIMITS
from ...utils import to_dict
from backend.utils.encryption import encrypt_config
from backend.services.tenant_manager import MultiTenantDBManager

class TentCRUD:
    @staticmethod
    def create(db: Session, tent_data: Union[dict, BaseModel], actor_id: Optional[int] = None) -> TentDatabase:
        from .company_events import CompanyCRUD # Lazy Import

        data = to_dict(tent_data)

        data = TentCRUD._get_encrypt_config(data)
        
        company_id = data.get('company_id')
        
        if company_id:
            company = CompanyCRUD.get_by_id(db, company_id)
            if company:
                limits = PLAN_LIMITS.get(company.plan, PLAN_LIMITS["free"])
                
                if company.databases_count >= limits["dbs"]:
                    raise ValueError(f"Plan limit reached. You can only have {limits['dbs']} databases.")
                
                company_old_snapshot = get_current_snapshot(company)
        
        new_tent = TentDatabase(**data)
        db.add(new_tent)
        db.flush()

        if new_tent.company_id and company:
            company.databases_count += 1
            record_modification(db, TableName.COMPANIES, company.company_id, ActionType.UPDATE, actor_id, company_old_snapshot)

        record_modification(db, TableName.TENTS, new_tent.db_id, ActionType.CREATE, actor_id, None)

        db.commit()
        db.refresh(new_tent)
        return new_tent

    @staticmethod
    def get_by_id(db: Session, db_id: int) -> Optional[TentDatabase]:
        return db.query(TentDatabase).filter(TentDatabase.db_id == db_id).first()
    
    @staticmethod
    def get_tents_by_company(db: Session, company_id: int) -> List[TentDatabase]:
        return db.query(TentDatabase).filter(TentDatabase.company_id == company_id).order_by(desc(TentDatabase.db_created_at)).all()
    
    @staticmethod
    def get_tents_list(db: Session, company_id: int) -> List[str]:
        tents = db.query(TentDatabase).filter(
            TentDatabase.company_id == company_id,
            TentDatabase.is_active == True
        ).all()

        return [
            {
                "id": t.db_id,
                "name": t.db_name
            } for t in tents
        ]
    
    @staticmethod
    def get_tables_schema(db: Session, company_id: int, selected_tent_ids: List[int]) -> Dict[str, List[str]]:
        tables_dict = {}

        tent_data = db.query(TentDatabase).filter(
            TentDatabase.company_id == company_id,
            TentDatabase.db_id.in_(selected_tent_ids),
            TentDatabase.is_active == True
        ).all()

        for tent in tent_data:
            tables_dict[tent.db_id] = tent.cached_schema or []
                
        return tables_dict
    
    @staticmethod
    def get_all(db: Session) -> List[TentDatabase]:
        return db.query(TentDatabase).join(Company).order_by(Company.company_name).all()

    @staticmethod
    def update(db: Session, db_id: int, updated_data: Union[dict, BaseModel], actor_id: Optional[int] = None) -> Optional[TentDatabase]:
        tent_record = TentCRUD.get_by_id(db, db_id)
        if tent_record:
            snapshot_before_update = get_current_snapshot(tent_record)
            data = to_dict(updated_data, for_update=True)

            data = TentCRUD._get_encrypt_config(data)

            for key, value in data.items():
                if hasattr(tent_record, key):
                    setattr(tent_record, key, value)

            record_modification(db, TableName.TENTS, db_id, ActionType.UPDATE, actor_id, snapshot_before_update)
            db.commit()
            db.refresh(tent_record)
        return tent_record

    @staticmethod
    def delete(db: Session, db_id: int, actor_id: Optional[int] = None) -> bool:
        from .company_events import CompanyCRUD # Lazy Import

        tent_record = TentCRUD.get_by_id(db, db_id)
        if tent_record:
            if tent_record.company_id:
                company = CompanyCRUD.get_by_id(db, tent_record.company_id)
                if company:
                    company_old_snapshot = get_current_snapshot(company)
                    company.databases_count -= 1
                    record_modification(db, TableName.COMPANIES, company.company_id, ActionType.UPDATE, actor_id, company_old_snapshot)

            record_modification(db, TableName.TENTS, db_id, ActionType.DELETE, actor_id, get_current_snapshot(tent_record))
            
            MultiTenantDBManager.disconnect_tent(db_id)
            
            db.delete(tent_record)
            db.commit()
            return True
        return False
    
    @staticmethod
    def _get_encrypt_config(data: dict):
        if data.get('connection_config'):
                data['connection_config'] = encrypt_config(data['connection_config'])
        return data