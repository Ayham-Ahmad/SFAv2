from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..models import User, Company, TentDatabase, Modification
from ...constants import TableName, ActionType

def _get_id_column_name(target: str): # ✅
    if target == TableName.USERS:
        return User.user_id.key
    elif target == TableName.COMPANIES:
        return Company.company_id.key
    elif target == TableName.TENTS:
        return TentDatabase.db_id.key
    
def _get_entity(db: Session, entity_id: int, target: str): # ✅
    """
        this fucntion is used to get an entity by id
        it returns an obj type of user, company, or tent models
    """

    model = {TableName.USERS: User, TableName.COMPANIES: Company, TableName.TENTS: TentDatabase}.get(target)
        
    if not model:
        print(f"[{Path(__file__).name}] Model name is not here")
        return None
    
    id_attr = getattr(model, _get_id_column_name(target))
    return db.query(model).filter(id_attr == entity_id).first()

def get_current_snapshot(entity, exclude_modify_key: bool = True): # ✅
    """
        this function is just to return a snapshot for a row for a current entity status
    """
    if not entity:
        return None
        
    snapshot = {}
    for c in entity.__table__.columns:
        if exclude_modify_key and c.name == 'modify_key':
            continue
            
        value = getattr(entity, c.name)
        if isinstance(value, datetime):
            snapshot[c.name] = value.isoformat()
        else:
            snapshot[c.name] = value
            
    return snapshot

def record_modification(db: Session, target_table: str, entity_id: int, action_type: str, user_id: Optional[int] = None, old_snapshot=None): # ✅
    """
        to use this function:
        1- use get_current_snapshot() to get the snapshot before the action
        2- make the action
        3- then just pass the old snapshot as old_snapshot
        4- commit
    """

    new_snapshot = None
    
    entity = _get_entity(db, entity_id, target_table)

    if entity:
        modify_key = entity.modify_key

        if action_type in [ActionType.CREATE, ActionType.UPDATE]:
            new_snapshot = get_current_snapshot(entity)

        db.query(Modification).filter(
            Modification.modify_key == modify_key, 
            Modification.is_last_modified == True
        ).update({Modification.is_last_modified.key: False}, synchronize_session=False)

        new_modify = Modification(
            modify_key=modify_key, 
            user_id=user_id,
            table_name=target_table, 
            action_type=action_type,
            previous_value=old_snapshot, 
            snapshot=new_snapshot, 
            is_last_modified=True
        )
        
        db.add(new_modify)

def get_modifications_by_entity(db: Session, target: str, entity_id): # ✅
    """
        this function is to get all the modifications for an etity
    """
    entity = _get_entity(db, entity_id, target)

    if not entity:
        return []
    
    return db.query(Modification).filter(
        Modification.modify_key == entity.modify_key
    ).order_by(Modification.modified_at.desc()).all()

def get_all_modifications(db: Session): # ✅
    """
        this function is to list all the modifications
    """
    return db.query(Modification).order_by(Modification.modified_at.desc()).all()