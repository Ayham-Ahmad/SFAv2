### retrieve_tool — executes SQL/NoSQL queries against tenant databases.
import asyncio
import datetime
import pandas as pd
import sentry_sdk
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from api.config import settings
from api.database.events.tent_events import TentCRUD
from backend.services.tenant_manager import MultiTenantDBManager
from api.constants import DatabaseType
from ..utils.clean import sanitize_multiTent_dataframe, is_query_safe
from ..utils.responses import create_response
from .base_tool import BaseTool


class RetrievalTool(BaseTool):
    """
    Executes SQL queries against connected tenant databases.
    Input: {"db_id": ["SELECT col FROM table LIMIT 10", ...], ...}
    """
    name = "retrieval"
    description = (
        "Executes SQL queries against the specified tent(s). "
        "Input: a dictionary mapping tent_id to a list of SQL query strings. "
        "Output: tabular data from the database."
    )
    input_type = dict
    requires_retrieval = False
    input_format = '{"tent_id_1": ["query1", "query2"], "tent_id_2": ["query"]}'

    def execute(self, input_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        db         = context.get("db")
        company_id = context.get("company_id")
        loop       = context.get("event_loop")

        if not db or not company_id:
            return {"success": False, "error": "Missing database session or company_id in context."}

        result = execute_multiTent_queries(db, company_id, input_data, loop)

        if result.get("success"):
            return {"success": True, "data": result.get("data", {}).get("results", {})}
        return {"success": False, "error": result.get("error", "Unknown DB Error")}


def _run_coroutine(coro, loop: asyncio.AbstractEventLoop):
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


def execute_multiTent_queries(
    db: Session,
    company_id: int,
    query_mapping: Dict[int, List[Any]],
    loop: asyncio.AbstractEventLoop,
) -> Dict[str, Any]:

    final_results = {"results": {}}
    errors = []

    try:
        for db_id, queries in query_mapping.items():
            tent = TentCRUD.get_by_id(db, int(db_id))

            if not tent or tent.company_id != company_id:
                err_msg = f"Unauthorized or missing Tent: {db_id}"
                errors.append(err_msg)
                sentry_sdk.capture_message(err_msg, level="warning")
                continue

            db_key = str(db_id)
            final_results["results"].setdefault(db_key, [])

            for sql_query in queries:
                if not sql_query:
                    continue

                raw_query_str = sql_query.get("query", "") if isinstance(sql_query, dict) else sql_query

                is_safe, safety_error = is_query_safe(raw_query_str, tent.db_type)
                if not is_safe:
                    errors.append({"db_id": db_id, "error": safety_error})
                    final_results["results"][db_key].append([{"error": safety_error}])
                    continue

                execution_response = _run_coroutine(
                    MultiTenantDBManager.execute_query_for_tent(tent, raw_query_str.strip()),
                    loop
                )

                if not execution_response.get("success"):
                    db_err = (
                        execution_response.get("error")
                        or execution_response.get("message")
                        or "Unknown DB execution error"
                    )
                    errors.append({"db_id": db_id, "error": db_err})
                    final_results["results"][db_key].append([{"error": db_err}])
                    continue

                payload = execution_response.get("data", {})
                rows    = payload.get("rows", [])
                columns = payload.get("columns", [])

                if not rows:
                    final_results["results"][db_key].append([])
                    continue

                df = pd.DataFrame(rows, columns=columns)

                if tent.db_type == DatabaseType.MONGODB:
                    df = sanitize_multiTent_dataframe(df)

                for col in df.columns:
                    try:
                        converted = pd.to_numeric(df[col], errors="coerce")
                        if not converted.isna().all():
                            df[col] = converted
                    except Exception as e:
                        sentry_sdk.capture_exception(e)

                for col in df.columns:
                    sample = df[col].dropna()
                    if not sample.empty and isinstance(sample.iloc[0], (datetime.date, datetime.datetime)):
                        df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
                        continue
                    if df[col].dtype in ["int64", "float64"] and not sample.empty:
                        val = sample.iloc[0]
                        try:
                            if abs(val) > 1e15:
                                df[col] = pd.to_datetime(df[col], unit="us").dt.strftime("%Y-%m-%d")
                            elif abs(val) > 1e12:
                                df[col] = pd.to_datetime(df[col], unit="ms").dt.strftime("%Y-%m-%d")
                        except (ValueError, OverflowError, OSError):
                            pass

                numeric_cols = df.select_dtypes(include=["number"]).columns
                df[numeric_cols] = df[numeric_cols].round(2)

                date_cols = [
                    c for c in df.columns
                    if df[c].dtype == "object" and df[c].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
                ]
                if not date_cols:
                    date_cols = [
                        c for c in df.columns
                        if c.lower() in ("date", "fiscaldateending", "fiscal_date_ending", "period", "quarter_date")
                    ]
                if date_cols:
                    df = df.sort_values(by=date_cols[0], ascending=True).reset_index(drop=True)

                df_final = df.where(pd.notnull(df), None)
                final_results["results"][db_key].append(
                    df_final.head(settings.ROW_LIMIT).to_dict(orient="records")
                )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        errors.append({"error": "Internal executor error", "details": str(e)})

    if errors:
        final_results["errors"] = errors

    return create_response(success=True, data=final_results, error=final_results.get("errors"))