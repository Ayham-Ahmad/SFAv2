import pandas as pd
import numexpr
import numpy as np
import sentry_sdk
from typing import Dict, Any, List

def calculate_on_multiTent_data(sql_results: Dict[str, List[List[Dict[str, Any]]]], formula: str, new_column_name: str = "computed_result") -> Dict[str, Any]:
    if not isinstance(sql_results, dict):
        return {"success": False, "error": "Math tool requires a valid results dictionary."}
    
    try:
        updated_results = {}
                
        for db_id, datasets in sql_results.items():
            updated_results[db_id] = []
            
            for rows in datasets:
                if not rows:
                    updated_results[db_id].append([])
                    continue

                df = pd.DataFrame(rows)
                                
                for col in df.columns:
                    if df[col].dtype in ['float64', 'int64']:
                        df[f"{col}_prev"] = df[col].shift(-1)

                calc_context = {col: df[col].values for col in df.columns if df[col].dtype in ['float64', 'int64']}
                
                try:
                    result_array = numexpr.evaluate(formula, local_dict=calc_context)
                    df[new_column_name] = result_array
                    
                    df[new_column_name] = (
                        df[new_column_name]
                        .replace([np.inf, -np.inf], np.nan)
                        .fillna(0.0)
                        .round(2)
                    )
    
                    updated_results[db_id].append(df[[new_column_name]].to_dict(orient="records"))
                except Exception as calc_err:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("db_id", db_id)
                        scope.set_extra("formula", formula)
                        scope.set_extra("available_cols", list(calc_context.keys()))
                        sentry_sdk.capture_exception(calc_err)
                    
                    updated_results[db_id].append(rows)
                    continue

        return {
            "success": True,
            "data": { "results": updated_results }
        }
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return {
            "success": False,
            "error": f"Global calculation failed: {str(e)}"
        }