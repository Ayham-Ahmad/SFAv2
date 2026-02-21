import re
import json
from typing import Dict, Any
import pandas as pd

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