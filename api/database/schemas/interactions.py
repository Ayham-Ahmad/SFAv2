from datetime import datetime
from typing import Optional
from pydantic import Field

from ...constants import AIModel, InteractionStatus
from .base import BaseSchema
from api.config import settings


class InteractionOut(BaseSchema):
    interaction_id: int
    model_used:     Optional[dict]               = None
    status:         InteractionStatus
    user_feedback:  Optional[bool]              = None
    response_time:  Optional[float]             = None
    api_call_count: Optional[int]               = None
    memory_usage:   Optional[float]             = None
    created_at:     datetime


class InteractionCreate(BaseSchema):
    session_id: int


class ChatRequest(BaseSchema):
    message: str = Field(
        ...,
        min_length=1,
        max_length=settings.CHAT_MESSAGE_MAX_LENGTH,
    )
    status: InteractionStatus = InteractionStatus.PENDING


class Performance(BaseSchema):
    response_time:  float
    api_call_count: int
    memory_usage:   float


def get_usage_metrics_dict() -> dict:
    return {
        "model_tokens": {},
        "api_call":    0,
        "steps": {
            "retrieval": 0,
            "advisory":  0,
            "math":      0,
            "graph":     0,
        },
    }

class DashboardOut(BaseSchema):
    active_users: int
    companies: int
    llm_cost: float
    active_databases: int
    total_interactions: int