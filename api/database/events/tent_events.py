from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Union, Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime, timezone

from ..models import TentDatabase, Company
from .modify_events import record_modification, get_current_snapshot
from ...constants import TableName, ActionType, PLAN_LIMITS, DatabaseType
from ...utils import to_dict
from backend.utils.encryption import encrypt_config
from backend.services.tenant_manager import MultiTenantDBManager


class TentCRUD:
    @staticmethod
    def create(
        db: Session, tent_data: Union[dict, BaseModel], actor_id
    ) -> TentDatabase:
        from .company_events import CompanyCRUD  # Lazy Import
        from .user_events import UserCRUD # Lazy Import

        data = to_dict(tent_data)
        data = TentCRUD._get_encrypt_config(data)
        company_id = data.get("company_id")

        company = None
        if company_id:
            company = CompanyCRUD.get_by_id(db, company_id)
            admin = UserCRUD.get_admin_by_company_id(db, company_id)
            if company and admin.user_id == actor_id:
                limits = PLAN_LIMITS.get(company.plan, PLAN_LIMITS["free"])

                if company.databases_count >= limits["dbs"]:
                    raise ValueError(
                        f"Plan limit reached. You can only have {limits['dbs']} databases."
                    )

                company_old_snapshot = get_current_snapshot(company)
                
            else:
                print("You are not Authorized")
                return 0
            
        new_tent = TentDatabase(**data)

        schema_response = MultiTenantDBManager.get_schema_for_tent(new_tent)
        
        if not schema_response.get("success"):
            raise ValueError(f"Failed to connect and verify database: {schema_response.get('message')}")

        res_data = schema_response.get("data", {})
        incoming_table_count = res_data.get("total_tables", 0)

        if (company.total_tables_count + incoming_table_count) > limits["tables"]:
            raise ValueError(
                f"Table limit reached. This would bring your total to "
                f"{company.total_tables_count + incoming_table_count}/{limits['tables']} tables."
            )            
        
        if new_tent.db_type == DatabaseType.CSV:
            incoming_size_mb = res_data.get("total_size_mb", 0.0)
            if (company.total_storage_mb + incoming_size_mb) > limits["storage_mb"]:
                raise ValueError(
                    f"Storage limit reached. This CSV ({incoming_size_mb}MB) would exceed "
                    f"your remaining quota of {round(limits['storage_mb'] - company.total_storage_mb, 2)}MB."
                )

        new_tent.cached_schema = res_data
        new_tent.is_connected = True
        new_tent.last_synced = datetime.now(timezone.utc)

        db.add(new_tent)
        db.flush()

        if company:
            company.databases_count += 1
            company.total_tables_count += incoming_table_count
            
            if new_tent.db_type == "csv":
                company.total_storage_mb += incoming_size_mb

            record_modification(
                db,
                TableName.COMPANIES,
                company.company_id,
                ActionType.UPDATE,
                actor_id,
                company_old_snapshot,
            )

        record_modification(
            db, TableName.TENTS, new_tent.db_id, ActionType.CREATE, actor_id, None
        )

        db.commit()
        db.refresh(new_tent)
        return new_tent

    @staticmethod
    def get_by_id(db: Session, db_id: int) -> Optional[TentDatabase]:
        return db.query(TentDatabase).filter(TentDatabase.db_id == db_id).first()

    @staticmethod
    def get_tents_by_company(db: Session, company_id: int) -> List[TentDatabase]:
        return (
            db.query(TentDatabase)
            .filter(TentDatabase.company_id == company_id)
            .order_by(desc(TentDatabase.db_created_at))
            .all()
        )

    @staticmethod
    def get_tents_list(db: Session, company_id: int) -> List[str]:
        tents = (
            db.query(TentDatabase)
            .filter(
                TentDatabase.company_id == company_id, TentDatabase.is_active == True
            )
            .all()
        )

        return [{"id": t.db_id, "name": t.db_name} for t in tents]

    @staticmethod
    def get_tables_schema(
        db: Session, company_id: int, selected_tent_ids: List[int]
    ) -> Dict[str, List[str]]:
        
        if isinstance(selected_tent_ids, int):
            selected_tent_ids = [selected_tent_ids]
        
        tables_dict = {}

        tent_data = (
            db.query(TentDatabase)
            .filter(
                TentDatabase.company_id == company_id,
                TentDatabase.db_id.in_(selected_tent_ids),
                TentDatabase.is_active == True,
            )
            .all()
        )

        for tent in tent_data:
            schema_data = tent.cached_schema or {}
            tables_metadata = schema_data.get("tables", {})
            
            simplified_tables = {
                table_name: meta.get("columns", [])
                for table_name, meta in tables_metadata.items()
            }
            
        tables_dict[tent.db_id] = simplified_tables

        return tables_dict

    @staticmethod
    def get_all(db: Session) -> List[TentDatabase]:
        return db.query(TentDatabase).join(Company).order_by(Company.company_name).all()

    @staticmethod
    def update(
        db: Session, db_id: int, updated_data: Union[dict, BaseModel], actor_id
    ) -> Optional[TentDatabase]:
        tent_record = TentCRUD.get_by_id(db, db_id)
        if tent_record:
            snapshot_before_update = get_current_snapshot(tent_record)
            data = to_dict(updated_data, for_update=True)

            data = TentCRUD._get_encrypt_config(data)

            for key, value in data.items():
                if hasattr(tent_record, key):
                    setattr(tent_record, key, value)

            record_modification(
                db,
                TableName.TENTS,
                db_id,
                ActionType.UPDATE,
                actor_id,
                snapshot_before_update,
            )
            db.commit()
            db.refresh(tent_record)
        return tent_record

    @staticmethod
    def delete(db: Session, db_id: int, actor_id: int) -> bool:
        from .company_events import CompanyCRUD  # Lazy Import

        tent_record = TentCRUD.get_by_id(db, db_id)
        if tent_record:
            if tent_record.company_id:
                company = CompanyCRUD.get_by_id(db, tent_record.company_id)
                if company:
                    company_old_snapshot = get_current_snapshot(company)
                    
                    company.databases_count = max(0, company.databases_count -1)
                    old_schema_data = tent_record.cached_schema or {}
                    tables_to_remove = old_schema_data.get("total_tables", 0)
                    company.total_tables_count = max(0, company.total_tables_count - tables_to_remove)
                    
                    if tent_record.db_type == DatabaseType.CSV:
                        size_to_remove = old_schema_data.get("total_size_mb", 0.0)
                        company.total_storage_mb = max(0.0, company.total_storage_mb - size_to_remove)
                    
                    record_modification(
                        db,
                        TableName.COMPANIES,
                        company.company_id,
                        ActionType.UPDATE,
                        actor_id,
                        company_old_snapshot,
                    )

            record_modification(
                db,
                TableName.TENTS,
                db_id,
                ActionType.DELETE,
                actor_id,
                get_current_snapshot(tent_record),
            )

            MultiTenantDBManager.disconnect_tent(db_id)

            db.delete(tent_record)
            db.commit()
            return True
        return False

    @staticmethod
    def _get_encrypt_config(data: dict):
        if data.get("connection_config"):
            data["connection_config"] = encrypt_config(data["connection_config"])
        return data
