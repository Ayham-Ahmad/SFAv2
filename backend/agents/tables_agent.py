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
You are a Database Schema Mapper. Your task is to match the user query to specific tables within the provided Database IDs.

AVAILABLE SCHEMAS:
{json.dumps(tables_schema, indent=2)}

USER QUERY: "{user_query}"

CRITICAL RULES:
1. You MUST use the exact Database IDs provided in the SCHEMA DATA above as your JSON keys.
2. If a query requires data from multiple IDs (e.g., comparing Google and Apple), provide a entry for EACH ID.
3. Only include tables that actually exist under that specific ID in the provided schema.
4. Return ONLY valid JSON. No explanations, no markdown.

RESPONSE FORMAT:
{{
  "3": ["aapl_historical"],
  "4": ["googl_daily_prices"]
}}
"""
    try:
        response = call_llm(prompt, model=AIModel.LLAMA_31_8B)
        
        json_matches = re.findall(r"\{[\s\S]*?\}", response)
        if json_matches:
            json_str = next((m for m in reversed(json_matches) if re.search(r'"\d+"', m)), json_matches[-1])
            raw_data = json.loads(json_str.replace("'", '"'))
            
            final_mapping = {}
            for db_id_str, tables in raw_data.items():
                db_id = int(db_id_str)
                if db_id in tables_schema:
                    table_list = tables if isinstance(tables, list) else []
                    final_mapping[db_id] = [t for t in table_list if t in tables_schema[db_id]]
            return final_mapping
            
        return {tid: [] for tid in tents_ids}
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return {tid: [] for tid in tents_ids}