"""
This agent is to choose which of the user tents we are going to use to answer the user question

Input: user query
output: a list of tents IDs
"""

import sentry_sdk
from sqlalchemy.orm import Session
from typing import List

from ..core.llm_client import call_llm
from api.database.events.tent_events import TentCRUD
from api.constants import AIModel
from ..services.prompts import TentAgentPrompt
from ..utils.clean import prepare_tents_summary, clean_tents_response

def get_relevant_tents(user_query: str, db: Session, company_id: int) -> List[int]:
    tents = TentCRUD.get_tents_by_company(db, company_id)
        
    if not tents:
        return []
    
    if len(tents) == 1:
        return [tents[0].db_id]  
    
    tents_summary, valid_ids = prepare_tents_summary(tents)  
        
    prompt = TentAgentPrompt.prompt(user_query, tents_summary)
    
    try:
        response = call_llm(prompt, model=AIModel.LLAMA_31_8B)
        
        return clean_tents_response(response, valid_ids)
    
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return [valid_ids]