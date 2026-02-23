"""
This agent is to choose which of the user tents we are going to use to answer the user question

Input: user query
output: a list of tents IDs
"""

import json
import sentry_sdk
from sqlalchemy.orm import Session
import re
from typing import List

from ..core.llm_client import call_llm
from api.database.events.tent_events import TentCRUD
from api.constants import AIModel
from ..services.prompts import TentAgentPrompt

def get_retlevant_tents(user_query: str, db: Session, company_id: int) -> List[int]:
    tents = TentCRUD.get_tents_by_company(db, company_id)
    if not tents:
        return []
    
    if len(tents) == 1:
        return [tents[0]['id']]

    tents_summary = "\n".join([f"ID: {t.db_id} | Name: {t.db_name}" for t in tents])
        
    prompt = TentAgentPrompt.prompt(user_query, tents_summary)
    
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