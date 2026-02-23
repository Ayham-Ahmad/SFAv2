import sentry_sdk
from typing import List, Dict

from ..core.llm_client import call_llm
from api.constants import AIModel
from ..services.prompts import TableAgentPrompt
from ..utils.clean import parse_table_agent_response

def get_relevant_tables(user_query: str, tents_ids: List[int], tables_schema) -> Dict[int, List[str]]:    
    
    prompt = TableAgentPrompt.prompt(user_query, tables_schema)
    try:
        response = call_llm(prompt, model=AIModel.LLAMA_31_8B)
        
        return parse_table_agent_response(response, tables_schema, tents_ids)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return {tid: [] for tid in tents_ids}