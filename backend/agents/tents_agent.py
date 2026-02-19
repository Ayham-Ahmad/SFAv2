import json
import sentry_sdk
from sqlalchemy.orm import Session
import re
from typing import List

from ..core.llm_client import call_llm
from api.database.events.tent_events import TentCRUD
from api.constants import AIModel

def get_retlevant_tents(user_query: str, db: Session, company_id: int) -> List[int]:
    tents = TentCRUD.get_tents_by_company(db, company_id)
    if not tents:
        return []
    
    if len(tents) == 1:
        return [tents[0]['id']]

    tents_summary = "\n".join([f"ID: {t.db_id} | Name: {t.db_name}" for t in tents])
    
    prompt = f"""
You are a Database Router. Based on the User Query, identify which Database IDs are necessary to answer the question.

AVAILABLE DATABASES:
{tents_summary}

USER QUERY: "{user_query}"

RULES:
1. Return ONLY a valid JSON list of integers representing the IDs.
2. If the query is general (e.g., "Give me a summary of all data"), return ALL IDs.
3. If no databases match the query, return an empty list []
4. Do not provide explanations or thought process, only the JSON list.

RESPONSE FORMAT:
[1, 2, 3]
"""
    try:
        response = call_llm(prompt, model=AIModel.LLAMA_31_8B)
        
        match = re.search(r"\[.*\]", response)

        if match:
            selected_ids = json.loads(match.group(0).strip())

            valid_ids = {t.db_id for t in tents}
            return [t_id for t_id in selected_ids if t_id in valid_ids]
        
        return []
    
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return [t['id'] for t in tents]