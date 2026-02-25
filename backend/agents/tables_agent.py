"""
This agent is used to choose which tables will be used to answer the user query

Input: user query, tables schema {db_id: list of tables}
Output: {db_id: {db_type: list of tables}}
"""

import sentry_sdk
from typing import List, Dict
from sqlalchemy.orm import Session

from ..core.llm_client import call_llm
from api.constants import AIModel
from ..services.prompts import TableAgentPrompt
from ..utils.clean import parse_table_agent_response
from api.database.events import TentCRUD

def get_relevant_tables(db: Session, user_query: str, tents_ids: List[int], tables_schema: Dict[int, List[str]]) -> Dict[int, List[str]]:
        
    if len(tents_ids) == 1:
        db_id, tables_list = next(iter(tables_schema.items()))
        tables_count = len(tables_list)
        if tables_count == 1:
            db_type = TentCRUD.get_by_id(db, db_id).db_type
            return {db_id: {db_type: tables_list}}
        elif tables_count <= 0:
            return {}

    prompt = TableAgentPrompt.prompt(user_query, tables_schema)
    try:
        response = call_llm(prompt, model=AIModel.LLAMA_31_8B)
        
        return parse_table_agent_response(db, response, tables_schema, tents_ids)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return {}