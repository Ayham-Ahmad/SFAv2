import asyncio
import time
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sentry_sdk

from api.deps import get_db, get_current_active_user
from api.database.models import Interaction, User
# from api.database.schemas import ChatRequest 
# from backend.pipeline.routing import run_text_query_pipeline
# from backend.pipeline.graph_pipeline import run_graph_pipeline
# from backend.core.logger import log_system_error
from backend.services.tenant_manager import MultiTenantDBManager
from api.config import settings
from api.database.events import TentCRUD, InteractionCRUD
from backend.utils.pricing import CostCalculator
from backend.utils.responses import create_response

# from backend.pipeline.progress import (
#     active_queries, 
#     query_progress, 
#     set_query_progress, 
#     clear_query_progress
# )

router = APIRouter(prefix="/api/chat", tags=["Chat"])

async def run_task_safely(task_func, query_id: str):
    task = asyncio.create_task(task_func())
    # active_queries[query_id] = task

    try: 
        result = await asyncio.wait_for(task, timeout=settings.TIMEOUT_SECONDS)

        if isinstance(result, dict):
            return result.get("output", result.get("message", "")), result.get("chart_data")
        return result, None
    
    except asyncio.TimeoutError:
        task.cancel()
        return "The analysis took too long. Try asking for a smaller date range.", None
    except Exception as e:
        sentry_sdk.capture_exception(e)
        # log_system_error(f"Chat Task Failed [{query_id}]: {e}") use sentry_sdk instaed
        return f"An error occurred during analysis: {str(e)}", None, False
    finally:
        # active_queries.pop(query_id, None)
        # clear_query_progress(query_id)
        pass

@router.post("")
async def chat_endpoint(
    # request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    1. Validate Tenant
    2. Create 'Processing' DB Record
    3. Run AI Pipeline
    4. Update DB Record (Complete/Failed)
    5. Return Response
    """

    start_time = time.time()
    # query_id = request.query_id or str(uuid4)

    tents = TentCRUD.get_tents_by_company(db, current_user.company_id)

    if not tents:
        return create_response(False, "⚠️ No database connected. Please ask an Admin to configure a Tent.")

    # is_graph = (request.interaction_type == "graph")
    # interaction_type = InteractionType.GRAPH_BUTTON if is_graph else InteractionType.QUERY

    # set_query_progress(query_id, "classifier", "🔍 Analyzing your request...")

    async def heavy_ai_task():
        # if is_graph:
            # return await asyncio.to_thread(run_graph_pipline, request.message, quer_id, current_user)
        # else: 
            # return await asyncio.to_thread(run_text_query_pipeline, request.message, quey_id, current_user)

    # answer_text, chart_data = await run_task_safely(heavy_ai_task, query_id)

        pass