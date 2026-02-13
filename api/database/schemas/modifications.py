from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any
from ...constants import TableName, ActionType
from .base import BaseSchema

class ModificationOut(BaseSchema):
    modify_id: int
    modify_key: str
    table_name: TableName
    action_type: ActionType
    previous_value: Optional[Any] = None 
    snapshot: Optional[Any] = None
    modified_at: datetime