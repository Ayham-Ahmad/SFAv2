from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional
from ...constants import DatabaseType
from .base import BaseSchema

class TentOut(BaseSchema):
    db_id: int
    db_name: str
    db_type: DatabaseType
    is_active: bool
    is_connected: bool = False
    cached_schema: Optional[Dict[str, Any]] = None
    last_synced: Optional[datetime] = None
    db_created_at: datetime

class TentCreate(BaseModel):
    db_name: str
    db_type: DatabaseType
    connection_config: Dict[str, Any]
    is_active: bool = True
    company_id: Optional[int] = None 

class TentUpdate(BaseModel):
    db_name: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class DatabaseQueryRequest(BaseModel):
    query: str
    db_id: int

class TentStatusSchema(BaseModel):
    db_id: int
    db_name: str
    db_type: DatabaseType
    is_connected: bool = False
    last_ping: Optional[datetime] = None