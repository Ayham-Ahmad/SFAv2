"""
This agent is to choose which of the user tents we are going to use to answer the user question

Input: user query
output: a list of tents IDs, updated usage_metrics
"""

import sentry_sdk
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple, Any

from ..core.llm_client import call_llm
from api.database.events.tent_events import TentCRUD
from api.constants import AIModel
from ..services.prompts import TentAgentPrompt
from ..utils.clean import prepare_tents_summary, clean_tents_response

async def get_relevant_tents(
    user_query: str,
    db: Session,
    company_id: int,
    usage_metrics: Dict[str, Any]
) -> Tuple[List[int], Dict[str, Any]]:

    tents = TentCRUD.get_tents_by_company(db, company_id)
    connected_tents = [t for t in tents if getattr(t, 'is_connected', False)]

    if not connected_tents:
        return [], usage_metrics

    if len(connected_tents) == 1:
        return [connected_tents[0].db_id], usage_metrics

    tents_summary, valid_ids = prepare_tents_summary(connected_tents)
    prompt = TentAgentPrompt.prompt(user_query, tents_summary)

    try:
        response, usage_metrics = await call_llm(
            prompt,
            model=AIModel.LLAMA_31_8B,
            usage_metrics=usage_metrics
        )
        selected = clean_tents_response(response, valid_ids)

        if not selected:
            print("Tents agent: no valid IDs parsed from model response — returning []")

        return selected, usage_metrics

    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Tents agent error: {e}")
        return [], usage_metrics
