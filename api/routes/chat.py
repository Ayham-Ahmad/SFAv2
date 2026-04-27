import time
import tracemalloc
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_active_user
from api.constants import PLAN_LIMITS
from api.database.models import User
from api.database.schemas import ChatRequest, InteractionCreate, Performance
from api.database.events import InteractionCRUD, SessionCRUD, CompanyCRUD
from backend.utils.responses import create_response
from backend.agents.SFA import SFA
from backend.utils.calculating import calculate_interaction_cost
from backend.core.task import run_task

router = APIRouter(prefix="/api/chat", tags=["Chat"])
templates = Jinja2Templates(directory="frontend/templates")

@router.get("/analytics", response_class=HTMLResponse)
async def get_chat_page(
    request: Request,
    # current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    mock_user = db.query(User).filter(User.user_id == 2).first() # change this to get_current_active_user
    
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "current_user": mock_user,
            "active_page": "analytics"
        }
    )

@router.post("")
async def chat_endpoint(
    http_request: Request,
    payload: ChatRequest,
    # current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    current_user = db.query(User).filter(User.user_id == 2).first()
    tracemalloc.start()
    start_time = time.time()
    
    company = CompanyCRUD.get_by_id(db, current_user.company_id)
    
    if not company:
        print("Error: No company found in chat_endpoint router")
        
    plan = PLAN_LIMITS.get(company.plan)
    
    model = plan["allowed_models"][1] # change this to dynamic based on the company's plan
    
    current_session = SessionCRUD.get_active_by_user(db, current_user.user_id)
    
    if not current_session:
        print("Error: No current session found in chat_endpoint")
    
    interaction = InteractionCRUD.create(
        db=db,
        interaction_data=InteractionCreate(session_id=1) # change this to current_session.session_id
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
    api_call_count = usage_metrics.get("api_call", 0)
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