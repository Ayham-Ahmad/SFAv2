import pandas as pd
import numexpr
from typing import Dict, Any, List

def calculate_on_multitent_data(
    sql_results: Dict[str, List[Dict[str, Any]]], 
    formula: str,
    new_column_name: str = "computed_result"
) -> Dict[str, Any]:
    try:
        updated_results = {}
        
        for db_id, rows in sql_results.items():
            if not rows:
                updated_results[db_id] = []
                continue

            df = pd.DataFrame(rows)

            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='ignore')

            calc_context = {
                col: df[col].values 
                for col in df.columns 
                if df[col].dtype in ['int64', 'float64', 'float32']
            }
            
            try:
                df[new_column_name] = numexpr.evaluate(formula, local_dict=calc_context)
                updated_results[db_id] = df.to_dict(orient="records")
            except Exception as e:
                updated_results[db_id] = rows
                continue

        return {
            "success": True,
            "data": {
                "results": updated_results
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Global calculation failed: {str(e)}"
        }
        

# adding some tables to the testing databases
# check the count of the tables for each user and the size in MB
# how to check if it is really a financial database or not
# continue the calc toolf