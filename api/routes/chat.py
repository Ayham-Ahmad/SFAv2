import time
import tracemalloc
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_active_user
from api.constants import PLAN_LIMITS
from api.database.models import User
from api.database.schemas import ChatRequest, InteractionCreate, Performance
from api.database.events import InteractionCRUD, SessionCRUD, CompanyCRUD
from api.database.events.graphs_events import GraphsCRUD
from backend.utils.responses import create_response
from backend.agents.SFA import SFA
from backend.core.task import run_task

router = APIRouter(prefix="/api/chat", tags=["Chat"])
templates = Jinja2Templates(directory="frontend/templates")


@router.get("/analytics", response_class=HTMLResponse)
async def get_chat_page(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "current_user": current_user, "active_page": "analytics"},
    )


@router.post("")
async def chat_endpoint(
    http_request: Request,
    payload: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tracemalloc.start()
    start_time = time.time()

    company = CompanyCRUD.get_by_id(db, current_user.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    plan  = PLAN_LIMITS.get(company.plan, {})
    model = plan.get("allowed_models", [])[-1]  ### use the best model the plan allows

    session = SessionCRUD.get_active_by_user(db, current_user.user_id)
    if not session:
        session = SessionCRUD.create(db, current_user.user_id)

    interaction = InteractionCRUD.create(
        db=db,
        interaction_data=InteractionCreate(session_id=session.session_id),
    )

    agent = SFA(
        user_query=payload.message,
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.user_id,
        session_id=session.session_id,
    )

    answer_text, usage_metrics, graph_data = await run_task(agent, http_request)

    response_time    = round(time.time() - start_time, 2)
    _, peak_mem      = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    memory_usage_mb  = round(peak_mem / (1024 * 1024), 2)

    api_call_count = usage_metrics.get("api_call", 0)
    steps          = usage_metrics.get("steps", {})
    model_tokens   = usage_metrics.get("model_tokens", {})

    for graph_config in graph_data:
        GraphsCRUD.create(db, graph_config, current_user.user_id, session.session_id)

    InteractionCRUD.complete_interaction(
        db=db,
        interaction_id=interaction.interaction_id,
        content={"answer": answer_text},
        steps=steps,
        model_used=model_tokens,
        performance_data=Performance(
            response_time=response_time,
            api_call_count=api_call_count,
            memory_usage=memory_usage_mb,
        ).model_dump(),
    )

    event_bus = http_request.app.state.event_bus
    await event_bus.publish("dashboard_update", {})

    return create_response(
        success="An error occurred" not in answer_text,
        message=answer_text,
        data={"graphs": graph_data} if graph_data else None,
    )


@router.post("/stop")
async def stop_chat(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = SessionCRUD.get_active_by_user(db, current_user.user_id)
    if session:
        SessionCRUD.set_stop_signal(db, session.session_id)
    return {"success": True, "message": "Stop signal sent."}


@router.get("/history")
async def get_chat_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = SessionCRUD.get_active_by_user(db, current_user.user_id)
    if not session:
        return create_response(True, data={"history": []})

    interactions = InteractionCRUD.get_entire_session_history(db, session.session_id)
    history = [
        {
            "interaction_id": i.interaction_id,
            "answer":         (i.interaction_content or {}).get("answer", ""),
            "created_at":     i.created_at.isoformat(),
            "status":         i.status,
        }
        for i in interactions
        if i.interaction_content
    ]
    return create_response(True, data={"history": history})