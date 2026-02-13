from pydantic import BaseModel
from typing import Optional, Any

class ManagerResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None

def create_response(success: bool, message: str = None, data: Any = None, error: str = None) -> dict:
    return ManagerResponse(
        success=success,
        message=message,
        data=data,
        error=error
    ).model_dump()