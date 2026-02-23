import re
import json
from typing import Dict, Any, List
import pandas as pd
import sentry_sdk

from api.constants import FORBIDDEN_KEYWORDS

def clean_sql(raw_sql: str) -> str:
    raw_sql = re.sub(r"```sql|```", "", raw_sql)
    return raw_sql.split(";")[0].strip()

def validate_read_only(sql: str) -> bool:
    normalized = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', normalized):
            return False
    return True
    
def extract_react_components(raw_llm_text: str) -> Dict[str, Any]:
    thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", raw_llm_text, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else ""

    if "Final Answer:" in raw_llm_text:
        final_answer = raw_llm_text.split("Final Answer:")[-1].strip()
        return {
            "thought": thought,
            "final_answer": final_answer,
            "action": None
        }

    action_match = re.search(r"Action:\s*(.*)", raw_llm_text)
    action_input_match = re.search(r"Action Input:\s*(\{.*\})", raw_llm_text, re.DOTALL)

    action = action_match.group(1).strip() if action_match else None
    
    action_input = None
    if action_input_match:
        try:
            action_input = json.loads(action_input_match.group(1))
        except json.JSONDecodeError:
            action_input = {"error": "Invalid JSON in Action Input"}

    return {
        "thought": thought,
        "action": action,
        "action_input": action_input
    }

def extract_final_outputs(output: str):
    return output
    pass

def sanitize_multitent_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(
                lambda x: list(x.values())[0] if isinstance(x, dict) and any(k in x for k in ['$numberDouble', '$numberInt', '$numberLong']) else x
            )
        
        try:
            converted = pd.to_numeric(df[col], errors='coerce')
            if not converted.isna().all():
                df[col] = converted
        except Exception:
            continue

    return df.where(pd.notnull(df), None)


def clean_and_parse_tools(raw_text: str) -> dict:
    try:
        json_pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(json_pattern, raw_text, re.DOTALL)
        clean_text = match.group(1) if match else raw_text
        
        return json.loads(clean_text.strip())
    except Exception as e:
        print(f"❌ JSON Parsing Error: {e}")
        return None
    
def clean_tables_schema(tables_schema: Dict[int, Dict[str, List[str]]]) -> Dict[int, Dict[str, List[str]]]:
    return {
        db_id: {
            table_name: [col.split(':')[0].strip() for col in columns]
            for table_name, columns in tables.items()
        }
        for db_id, tables in tables_schema.items()
    }
    
def clean_tables_schema_for_tableAgent(tables_schema, max_chars: int = 4000, max_name_len: int = 25):
    """
    1. make sure all tables names max char count <= max_name_len.
    2. make sure the max char len for all the tables schema <= max_chars.
    3. make sure all tables names has unique name.
    
    Input: {db_id: [{table_name: [{column_name: column_type}]}]}
    Output: {db_id: [tables_name]}
    """
    summary = {}
    for db_id, tables in tables_schema.items():
        table_names = list(tables.keys())
        
        unique_truncated_list = []
        seen_names = {}
        current_total_chars = 0
        
        for name in table_names:
            clean_name = name[:max_name_len] if len(name) > max_name_len else name
            
            if clean_name in seen_names:
                seen_names[clean_name] += 1
                suffix = f"~{seen_names[clean_name]}"
                clean_name = clean_name[:max_name_len - len(suffix)] + suffix
            else:
                seen_names[clean_name] = 0
            
            if current_total_chars + len(clean_name) + 4 > max_chars:
                unique_truncated_list.append("...LIST_TRUNCATED...")
                break
            
            unique_truncated_list.append(clean_name)
            current_total_chars += len(clean_name) + 4
            
        summary[db_id] = unique_truncated_list
            
    return summary


def parse_table_agent_response(raw_response: str, tables_schema: Dict[int, List[str]], tents_ids: List[int]) -> Dict[int, List[str]]:
    try:
        json_matches = re.findall(r"\{[\s\S]*?\}", raw_response)
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