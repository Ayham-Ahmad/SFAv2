import re
import ast
import json
import pandas as pd
import sentry_sdk
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from api.constants import FORBIDDEN_KEYWORDS, DatabaseType
from api.database.events import TentCRUD
from api.database.models import TentDatabase


def extract_react_components(raw_llm_text: str) -> Dict[str, Any]:
    thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", raw_llm_text, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else ""

    if "Final Answer:" in raw_llm_text:
        final_answer = raw_llm_text.split("Final Answer:")[-1].strip()
        return {
            "thought": thought,
            "action": "Final Answer",
            "action_input": final_answer
        }

    action_match = re.search(r"Action:\s*(.*?)(?=\nAction Input:|$)", raw_llm_text, re.DOTALL)
    action_input_match = re.search(r"Action Input:\s*(.*?)(?=\nAction:|\nObservation:|\nThought:|\nFinal Answer:|$)", raw_llm_text, re.DOTALL)

    action = action_match.group(1).strip() if action_match else None
    action_input_raw = action_input_match.group(1).strip() if action_input_match else ""

    action_input = None
    if action_input_raw:
        json_pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(json_pattern, action_input_raw, re.DOTALL)
        clean_json_str = match.group(1).strip() if match else action_input_raw.strip()

        try:
            action_input = json.loads(clean_json_str)
        except json.JSONDecodeError:
            action_input = {"error": "Invalid JSON in Action Input", "raw": action_input_raw}

    return {
        "thought": thought,
        "action": action,
        "action_input": action_input
    }


def sanitize_multiTent_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(
                lambda x: list(x.values())[0] if isinstance(x, dict) and any(
                    k in x for k in ['$numberDouble', '$numberInt', '$numberLong']
                ) else x
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
        print(f"[ERROR] JSON Parsing Error: {e}")
        return None


def clean_tables_schema(tables_schema, max_chars: int = 4000, max_name_len: int = 25):
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


def parse_table_agent_response(
    db: Session,
    raw_response: str,
    tables_schema: Dict[int, List[str]],
    tents_ids: List[int]
) -> Dict[int, List[str]]:
    try:
        json_matches = re.findall(r"\{[\s\S]*?\}", raw_response)
        if json_matches:
            json_str = next(
                (m for m in reversed(json_matches) if re.search(r'"\d+"', m)),
                json_matches[-1]
            )
            raw_data = json.loads(json_str.replace("'", '"'))

            final_mapping = {}
            for db_id_str, tables in raw_data.items():
                db_id = int(db_id_str)
                if db_id in tables_schema:
                    table_list = tables if isinstance(tables, list) else []
                    tent = TentCRUD.get_by_id(db, db_id)
                    if tent:
                        final_mapping[db_id] = {
                            tent.db_type: [t for t in table_list if t in tables_schema[db_id]]
                        }

            return final_mapping

        return {tid: [] for tid in tents_ids}
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return {tid: [] for tid in tents_ids}


def prepare_tents_summary(tents: List[TentDatabase]):
    valid_ids = [t.db_id for t in tents]
    tents_summary = "\n".join([f"ID: {t.db_id} | Name: {t.db_name}" for t in tents])
    return tents_summary, valid_ids


def clean_tents_response(response: str, valid_ids: List[int]):
    match = re.search(r"\[.*?\]", response)
    if match:
        try:
            selected_ids = ast.literal_eval(match.group(0).strip())
            if isinstance(selected_ids, list):
                return [int(t_id) for t_id in selected_ids if int(t_id) in valid_ids]
        except (ValueError, SyntaxError):
            return []
    return []


def get_chosen_tables_schema(tables, tents_schema):
    final_selected_schema = {}

    for db_id, db_info in tables.items():
        db_type = next(iter(db_info.keys()))
        selected_table_names = db_info[db_type]

        tables_with_columns = []
        for table_name in selected_table_names:
            if db_id in tents_schema and table_name in tents_schema[db_id]:
                raw_columns = tents_schema[db_id][table_name]
                clean_columns = [col.split(':')[0].strip() for col in raw_columns]
                tables_with_columns.append({table_name: clean_columns})

        final_selected_schema[db_id] = {db_type: tables_with_columns}

    return final_selected_schema


def is_query_safe(query: str, db_type: str) -> Tuple[bool, str]:
    
    if not query or not isinstance(query, str):
        return False, "Empty or invalid query format."

    if db_type == DatabaseType.MONGODB:
        forbidden_mongo = ["drop(", "deleteMany(", "deleteOne(", "remove(", "update", "insert"]
        if any(cmd in query for cmd in forbidden_mongo):
            return False, "Forbidden MongoDB destructive command detected."
        return True, ""

    normalized = query.strip().upper()
    collapsed = re.sub(r'\s+', ' ', normalized)

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', normalized):
            return False, f"Forbidden SQL command detected: {keyword}. Only SELECT is allowed."

    is_cte = collapsed.startswith("WITH ")
    is_show = collapsed.startswith("SHOW ")

    if not is_cte and not is_show and not collapsed.startswith("SELECT "):
        return False, "Query must start with SELECT (or WITH for CTEs, SHOW for schema inspection)."

    if is_cte and " SELECT " not in collapsed:
        return False, "CTE query must contain a SELECT statement in its body."

    if re.search(r'\bSELECT\s+\*', normalized):
        return False, "Prohibited use of 'SELECT *'. You MUST specify exact column names."

    if not is_show:
        has_limit = "LIMIT" in normalized
        has_count = bool(re.search(r'\bCOUNT\s*\(', normalized))
        if not has_limit and not has_count:
            return False, "Query missing LIMIT clause. All queries must include a LIMIT."

    return True, ""
