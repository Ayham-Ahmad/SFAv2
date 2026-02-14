import re
import json
from typing import Dict, Any, Optional

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