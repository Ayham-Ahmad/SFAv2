import pandas as pd
import sentry_sdk
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from api.database.events.tent_events import TentCRUD
from backend.services.tenant_manager import MultiTenantDBManager
from backend.utils.formatters import format_financial_value, format_date

def execute_multitent_queries(
    db: Session, 
    company_id: int, 
    query_mapping: Dict[int, Dict[str, Any]], 
    table_mapping: Dict[int, List[str]]
) -> Dict[str, Any]:
    
    final_results = {
        "results": {},
        "metadata": {"tables_queried": table_mapping},
        "errors": []
    }

    try:
        for db_id, task in query_mapping.items():
            sql_query = task.get("query")
            format_instructions = task.get("format", {})

            if not sql_query:
                continue

            tent = TentCRUD.get_by_id(db, db_id)
            if not tent or tent.company_id != company_id:
                final_results["errors"].append(f"Unauthorized or missing Tent ID: {db_id}")
                continue

            execution_response = MultiTenantDBManager.execute_query_for_tent(tent, sql_query.strip())

            if not execution_response.get("success"):
                final_results["errors"].append({"db_id": db_id, "error": execution_response.get("error")})
                continue

            rows = execution_response.get("rows", [])
            columns = execution_response.get("columns", [])

            if not rows:
                final_results["results"][db_id] = []
                continue

            df = pd.DataFrame(rows, columns=columns)

            for col_name, format_type in format_instructions.items():
                if col_name in df.columns:
                    if format_type == "financial":
                        df[col_name] = pd.to_numeric(df[col_name], errors='coerce').apply(
                            lambda x: format_financial_value(x, include_sign=False)
                        )
                    elif format_type == "date":
                        df[col_name] = df[col_name].apply(format_date)

            final_results["results"][db_id] = df.head(100).to_dict(orient="records")

    except Exception as e:
        sentry_sdk.capture_exception(e)
        final_results["errors"].append({"error": "Internal executor error", "details": str(e)})

    return final_results