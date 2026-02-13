from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from ...constants import AIModel, InteractionStatus
from .base import BaseSchema

class InteractionOut(BaseSchema):
    interaction_id: int
    model_used: Optional[AIModel] = None
    status: InteractionStatus
    cost: float
    user_feedback: Optional[bool] = None
    response_time: Optional[float] = None
    token_count: Optional[int] = None
    api_call_count: Optional[int] = None
    memory_usage: Optional[float] = None
    created_at: datetime