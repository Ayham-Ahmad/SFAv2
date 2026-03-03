from pydantic import BaseModel
from typing import Optional, Any

class ManagerResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[Any] = None

def create_response(success: bool, message: str = None, data: Any = None, error: str = None) -> dict:
    return ManagerResponse(
        success=success,
        message=message,
        data=data,
        error=error
    ).model_dump()
    
def get_fallback_response():
    return {
            "thought": "Max iterations reached.", 
            "action": "Final Answer", 
            "action_input": "I reached the maximum number of thinking steps without finding a complete answer."
        }