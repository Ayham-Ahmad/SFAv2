import re
import pandas as pd
import numexpr
import numpy as np
import sentry_sdk
from typing import Dict, Any, List

from .base_tool import BaseTool


class CalculatorTool(BaseTool):
    """
    Performs vectorized calculations on retrieved SQL data using numexpr.
    
    Input format from LLM:
        [[query_index, [columns], "formula"], ...]
    """
    name = "math"
    description = "Performs vectorized mathematical operations on retrieved data using numexpr."
    input_type = list
    requires_retrieval = True
    usage_guide = (
        "* **Input**: a list of [query_result_index, [column_names], \"equation\"]. "
        "* **Equation Rules**: Use raw column names directly (e.g., \"Revenue - Expenses\"). "
        "* **Vectorization**: To compare rows (like latest vs previous), use the suffix `_prev` for the previous row's value (e.g., \"Close - Close_prev\"). "
        "* **Aggregate Functions**: You can use AVG(Column), SUM(Column), MAX(Column), MIN(Column), COUNT(Column) in formulas. They are pre-computed to scalar values. Example: \"(Volume - AVG(Volume)) / AVG(Volume) * 100\" computes each row's deviation from the average. "
        "* **STRICT PROHIBITION**: NEVER use indices like `[0]` or `[1]`. `Close[0]` will cause a crash. Use `Close` for the current value and `Close_prev` for the previous value."
    )
    input_format = '[\n            [0, ["Close"], "(Close - Close_prev) / Close_prev * 100"]\n        ]'

    def execute(self, input_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        retrieval_results = context.get("retrieval_results")
        
        if not retrieval_results:
            return {"success": False, "error": "Math tool requires retrieval data. Call retrieval first."}

        math_results = []
        for calculation in input_data:
            if not isinstance(calculation, list) or len(calculation) < 3:
                math_results.append({"success": False, "error": "Each calculation must be [query_index, columns, formula]"})
                continue

            formula = calculation[2]
            if not isinstance(formula, str) or not formula.strip():
                math_results.append({"success": False, "error": "Formula must be a non-empty string."})
                continue

            calc_res = calculate_on_multiTent_data(retrieval_results, formula)
            math_results.append(calc_res)

        return {"success": True, "data": math_results}


def _resolve_aggregates(formula: str, df: pd.DataFrame) -> str:
    """Pre-compute aggregate functions (AVG, SUM, MAX, MIN, MEAN, COUNT) into scalar values
    before passing the formula to numexpr, which only supports element-wise operations."""
    agg_pattern = r'(AVG|SUM|MAX|MIN|MEAN|COUNT)\((\w+)\)'
    
    def replacer(match):
        func_name = match.group(1).upper()
        col_name = match.group(2)
        if col_name not in df.columns:
            raise ValueError(f"Column '{col_name}' not found for {func_name}() aggregation.")
        series = pd.to_numeric(df[col_name], errors='coerce')
        if func_name in ('AVG', 'MEAN'):
            return str(series.mean())
        elif func_name == 'SUM':
            return str(series.sum())
        elif func_name == 'MAX':
            return str(series.max())
        elif func_name == 'MIN':
            return str(series.min())
        elif func_name == 'COUNT':
            return str(series.count())
        return match.group(0)
    
    return re.sub(agg_pattern, replacer, formula)


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
                    resolved_formula = _resolve_aggregates(formula, df)
                    result_array = numexpr.evaluate(resolved_formula, local_dict=calc_context)
                    df[new_column_name] = result_array
                    
                    df[new_column_name] = (
                        df[new_column_name]
                        .replace([np.inf, -np.inf], np.nan)
                        .fillna(0.0)
                        .round(2)
                    )
    
                    # Collapse scalar results: if all values are identical (aggregate),
                    # return a single value instead of repeating it per row
                    unique_values = df[new_column_name].dropna().unique()
                    if len(unique_values) == 1:
                        # Convert numpy types to native Python for clean serialization
                        scalar_val = unique_values[0]
                        if hasattr(scalar_val, 'item'):
                            scalar_val = scalar_val.item()
                        updated_results[db_id].append([{new_column_name: scalar_val}])
                    else:
                        # Convert all values to native Python types
                        records = df[[new_column_name]].to_dict(orient="records")
                        for rec in records:
                            for k, v in rec.items():
                                if hasattr(v, 'item'):
                                    rec[k] = v.item()
                        updated_results[db_id].append(records)
                except Exception as calc_err:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("db_id", db_id)
                        scope.set_extra("formula", formula)
                        scope.set_extra("available_cols", list(calc_context.keys()))
                        sentry_sdk.capture_exception(calc_err)
                    
                    updated_results[db_id].append([{"error": f"Calculation failed for formula '{formula}': {str(calc_err)}"}])
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