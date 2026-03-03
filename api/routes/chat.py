import asyncio
import time
import tracemalloc
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import sentry_sdk

from api.deps import get_db, get_current_active_user
from api.config import settings
from api.constants import PLAN_LIMITS
from api.database.models import User
from api.database.schemas import ChatRequest, InteractionCreate, Performance, get_usage_metrics_dict
from api.database.events import InteractionCRUD, SessionCRUD, CompanyCRUD
from backend.utils.responses import create_response
from backend.agents.SFA import SFA
from backend.utils.calculating import calculate_interaction_cost

router = APIRouter(prefix="/api/chat", tags=["Chat"])

async def run_task(agent: SFA, http_request: Request):
    task = asyncio.create_task(agent.main(http_request))

    try: 
        result_data, usage_metrics = await asyncio.wait_for(task, timeout=settings.TIMEOUT_SECONDS)

        if isinstance(result_data, str):
            return result_data, usage_metrics

        if isinstance(result_data, dict):
            final_answer = result_data.get("action_input", "Analysis complete, but no output provided.")
            return final_answer, usage_metrics
        
        return "Unexpected response format.", usage_metrics
    
    except asyncio.TimeoutError:
        task.cancel()
        return "The analysis took too long. Try asking for a smaller date range.", get_usage_metrics_dict()
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return f"An error occurred during analysis: {str(e)}", get_usage_metrics_dict()


@router.post("")
async def chat_endpoint(
    http_request: Request,
    payload: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    tracemalloc.start()
    start_time = time.time()
    
    company_plan = CompanyCRUD.get_by_id(db, current_user.company_id).plan
    
    plan = PLAN_LIMITS.get(company_plan)
    
    model = plan["allowed_models"][1]
    
    current_session = SessionCRUD.get_active_by_user(db, current_user.user_id)
    
    interaction = InteractionCRUD.create(
        db=db,
        interaction_data=InteractionCreate(session_id=current_session.session_id)
    )

    agent = SFA(
        user_query=payload.message, 
        db=db, 
        company_id=current_user.company_id
    )

    answer_text, usage_metrics = await run_task(agent, http_request)

    response_time = time.time() - start_time
    
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    memory_usage_mb = peak_mem / (1024 * 1024)

    p_tokens = usage_metrics.get("p_tokens", 0)
    c_tokens = usage_metrics.get("c_tokens", 0)
    total_tokens = usage_metrics.get("total_tokens", 0)
    api_call_count = usage_metrics.get("api_calls", 0)
    steps = usage_metrics.get("steps", 0)
    

    estimated_cost = calculate_interaction_cost(model, p_tokens, c_tokens)
    
    performance_metrics = Performance(
        response_time=response_time,
        token_count=total_tokens,
        api_call_count=api_call_count, 
        memory_usage=memory_usage_mb
    )
    
    InteractionCRUD.complete_interaction(
        db=db,
        interaction_id=interaction.interaction_id,
        content=answer_text,
        steps=steps,
        model_used=model,
        cost=estimated_cost,
        performance_data=performance_metrics.model_dump()
    )

    return create_response(
        success=True if "An error occurred" not in answer_text else False, 
        message=answer_text,
    )