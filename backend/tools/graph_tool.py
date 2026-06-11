import sentry_sdk
from typing import List, Dict, Any

from .base_tool import BaseTool


class GraphTool(BaseTool):
    """
    Generates chart/graph configurations from retrieved SQL data.
    
    Input format from LLM:
        {"title": "Revenue", "type": "bar", "axis_titles": {...}, "query_result_index": 0}
    """
    name = "graph"
    description = "Generates a chart from retrieved data. Input: a JSON object with \"title\", \"type\" (line/bar/pie/etc.), \"axis_titles\" (with x/y titles and optional type), \"order\" (asc/desc for sorting), and \"query_result_index\" (0-based index of the retrieval result to plot). Output: a visual graph for the user. IMPORTANT: You may only generate ONE graph per response. Do NOT output arrays or multiple graph objects. If the user asks for multiple charts, just generate the most important one."
    input_type = dict
    requires_retrieval = True
    usage_guide = "When using this tool, the system will automatically save the generated graph to the user's dashboard. You should simply inform the user that their chart has been generated and is available to view."
    input_format = '{"title": "Quarterly Revenue", "type": "line", "axis_titles": {"x": {"title": "Date", "type": "date"}, "y": {"title": "Revenue (USD)", "type": "currency"}}, "order": "asc", "query_result_index": 0}'

    def execute(self, input_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        retrieval_results = context.get("retrieval_results")

        if not retrieval_results or "error" in str(retrieval_results):
            return {"success": False, "error": "Graph tool requires active retrieval data. Please call 'retrieval' in the same action."}

        graph_result = select_graph_template(input_data, retrieval_results)
        if graph_result.get("success"):
            return {"success": True, "data": graph_result}
        return graph_result


def select_graph_template(intent: dict, sql_results: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if not intent:
            return {"success": False, "error": "Empty input data"}
            
        # 1. Handle SQL results structure
        results_map = sql_results.get("results", sql_results)
        
        if not results_map:
            return {"success": False, "error": "No SQL results provided for graphing"}

        # 2. Determine which DB to use
        db_id = str(intent.get("db_id", ""))
        
        # If db_id is missing or not in results, default to the first available tenant
        if not db_id or db_id not in results_map:
            db_id = list(results_map.keys())[0]
                
        # 3. Get the specific dataset from that DB
        datasets = results_map.get(db_id, [])
        res_index = intent.get("query_result_index", 0)
        
        if not datasets or res_index >= len(datasets):
            return {"success": False, "error": f"Data not found for DB {db_id} index {res_index}"}
        
        raw_data = datasets[res_index]
        if not raw_data:
            return {"success": False, "error": "Dataset is empty"}

        # 4. Column and Axis Logic
        first_row = raw_data[0]
        available_cols = list(first_row.keys())

        axis_info = intent.get("axis_titles", {})
        x_info = axis_info.get("x", {})
        y_info = axis_info.get("y", {})
        
        x_col = x_info.get("title")
        y_col = y_info.get("title")
        
        if not x_col and available_cols:
            x_col = available_cols[0]
        if not y_col and len(available_cols) > 1:
            y_col = available_cols[1]
        elif not y_col and available_cols:
            y_col = available_cols[0]

        if not x_col or not y_col:
            return {"success": False, "error": "Could not determine X or Y columns"}

        # 5. Metadata and Formatting
        title = intent.get("title")
        if not title:
            title = f"{y_col} by {x_col}"

        graph_config = {
            "success": True,
            "graph_type": intent.get("type", "bar"),
            "title": title,
            "x_column": x_col,
            "x_format": x_info.get("type", "text"),
            "y_column": y_col,
            "y_format": y_info.get("type", "number"),
            "data": raw_data,
            "series": intent.get("series"),
            "axis_titles": intent.get("axis_titles")
        }

        # 6. Sorting
        if intent.get("order") == "asc":
            try:
                graph_config["data"] = sorted(raw_data, key=lambda x: x.get(x_col) if x.get(x_col) is not None else "")
            except Exception as sort_err:
                sentry_sdk.capture_message(f"Sort failed: {str(sort_err)}")

        return graph_config

    except Exception as e:
        sentry_sdk.capture_exception(e)
        return {"success": False, "error": f"Internal Error: {str(e)}"}