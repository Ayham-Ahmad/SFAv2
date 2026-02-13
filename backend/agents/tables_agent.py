import json
import re
import sentry_sdk
from typing import List, Dict
from sqlalchemy.orm import Session
from ..core.llm_client import call_llm
from api.database.events.tent_events import TentCRUD
from api.constants import AIModel

def get_relevant_tables(db: Session, company_id: int, user_query: str, tents_ids: List[int]) -> Dict[int, List[str]]:
    tables_schema = TentCRUD.get_tables_schema(db, company_id, tents_ids)

    prompt = f"""
Analyze the user query and identify the necessary tables for each Database ID.

AVAILABLE DATABASES:
{tables_schema}

USER QUERY: "{user_query}"

RULES:
1. Return ONLY a valid JSON object. 
2. Format: {{"ID": ["table1", "table2"]}}
3. If no tables match an ID, return "ID": [].
4. Do not include any markdown formatting, code blocks, or explanations.

RESPONSE FORMAT:
{{
  "1": ["orders", "products"],
  "2": [],
  "3": ["salaries"]
}}
"""
    try:
        response = call_llm(prompt, model=AIModel.LLAMA_31_8B)
        print("Raw:", response)

        json_matches = re.findall(r"\{[\s\S]*?\}", response)
        
        if json_matches:
            json_str = ""
            for match in reversed(json_matches):
                if re.search(r'"\d+"', match):
                    json_str = match
                    break
            
            if not json_str:
                json_str = json_matches[-1]

            json_str = json_str.replace("'", '"')
            raw_data = json.loads(json_str)
            
            final_mapping = {}
            for db_id_str, tables in raw_data.items():
                try:
                    db_id = int(db_id_str)
                    if db_id in tables_schema:
                        table_list = tables if isinstance(tables, list) else []
                        valid_tables = [t for t in table_list if t in tables_schema[db_id]]
                        final_mapping[db_id] = valid_tables
                except (ValueError, TypeError):
                    continue
            return final_mapping
            
        return {tid: [] for tid in tents_ids}
        
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return {tid: [] for tid in tents_ids}