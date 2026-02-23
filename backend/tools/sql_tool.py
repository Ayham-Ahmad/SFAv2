import pandas as pd
import sentry_sdk
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from api.database.events.tent_events import TentCRUD
from backend.services.tenant_manager import MultiTenantDBManager
from api.constants import DatabaseType
from ..utils.clean import sanitize_multitent_dataframe

def execute_multitent_queries(db: Session, company_id: int, query_mapping: Dict[int, List[Dict[str, Any]]]) -> Dict[str, Any]:
    final_results = {"results": {}}
    errors = []

    try:
        for db_name, queries in query_mapping.items():
            tent = TentCRUD.get_by_name(db, db_name)
            
            
            if not tent or tent.company_id != company_id:
                err_msg = f"Unauthorized or missing Tent: {db_name}"
                errors.append(err_msg)
                sentry_sdk.capture_message(err_msg, level="warning")
                continue

            db_id = tent.db_id
            db_key = str(db_id)
            if db_key not in final_results["results"]:
                final_results["results"][db_key] = []

            for sql_query in queries:
                if not sql_query:
                    continue

                execution_response = MultiTenantDBManager.execute_query_for_tent(tent, sql_query.strip())
                
                if not execution_response.get("success"):
                    db_err = execution_response.get("error")
                    errors.append({"db_id": db_id, "error": db_err})
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("tenant_id", db_id)
                        scope.set_extra("query", sql_query)
                        sentry_sdk.capture_message(f"DB Execution Failed for Tenant {db_id}", level="error")
                    continue
                
                payload = execution_response.get("data", {})
                rows = payload.get("rows", [])
                columns = payload.get("columns", [])

                if not rows:
                    final_results["results"][db_key].append([])
                    continue

                df = pd.DataFrame(rows, columns=columns)
                
                if tent.db_type == DatabaseType.MONGODB:
                    df = sanitize_multitent_dataframe(df)
                    
                for col in df.columns:
                    try:
                        converted = pd.to_numeric(df[col], errors='coerce')
                        if not converted.isna().all():
                            df[col] = converted
                    except Exception as e:
                        sentry_sdk.capture_exception(e)
                        continue
                
                numeric_cols = df.select_dtypes(include=['number']).columns
                df[numeric_cols] = df[numeric_cols].round(2)
                
                df_final = df.where(pd.notnull(df), None)
                final_results["results"][db_key].append(df_final.head(100).to_dict(orient="records"))

    except Exception as e:
        sentry_sdk.capture_exception(e)
        errors.append({"error": "Internal executor error", "details": str(e)})

    if errors:
        final_results["errors"] = errors

    return final_results