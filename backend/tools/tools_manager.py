from sqlalchemy.orm import Session
from ..utils.clean import clean_and_parse_tools
from .sql_tool import execute_multitent_queries
from .calculator_tool import calculate_on_multitent_data
from .graph_tool import select_graph_template
from .advisory_tool import AdvisoryRAGTool

def extract_sql_tool_inputs(tools_input: dict) -> dict | None:
    sql_data = tools_input.get("sql")
    if isinstance(sql_data, dict) and sql_data:
        return sql_data
    return None

def extract_math_tool_inputs(tools_input: dict) -> list | None:
    math_data = tools_input.get("math")
    if isinstance(math_data, list) and math_data:
        return math_data
    return None

def extract_advisory_tool_inputs(tools_input: dict) -> list | None:
    advisory_data = tools_input.get("advisory")
    if isinstance(advisory_data, list) and advisory_data:
        return advisory_data
    return None

def extract_graph_tool_inputs(tools_input: dict) -> dict | None:
    graph_data = tools_input.get("graph")
    if isinstance(graph_data, dict) and graph_data:
        return graph_data
    return None

class ToolsManager:
    
    @staticmethod
    async def main_agent_output_manager(db: Session, company_id: int, LLM_raw_output: str, request=None):
        data = clean_and_parse_tools(LLM_raw_output)
        if not data:
            return "Error: Could not parse your tool requests. Please ensure you output valid JSON."

        tools_input = data.get("tools", {})
        results = {}
        
        sql_payload = extract_sql_tool_inputs(tools_input)
        if sql_payload:
            results["sql"] = execute_multitent_queries(db, company_id, sql_payload)
            
        advisory_payload = extract_advisory_tool_inputs(tools_input)
        if advisory_payload and request:
            vector_db = getattr(request.app.state, "vector_db", None)
            if vector_db:
                rag_tool = AdvisoryRAGTool(vector_db)
                results["advisory"] = rag_tool.get_institutional_knowledge(advisory_payload)
            else:
                results["advisory"] = "Error: Knowledge Base not initialized."

        math_payload = extract_math_tool_inputs(tools_input)
        if math_payload:
            for calculation in math_payload:
                query_index = calculation[0]
                columns = calculation[1]
                formula = calculation[2]
                
                results["math"] = calculate_on_multitent_data(results.get("sql"), formula)

        graph_payload = extract_graph_tool_inputs(tools_input)
        if graph_payload:
            results["graph"] = select_graph_template(graph_payload, results.get("sql"))
            

        return ToolsManager.format_observation_prompt(results, data.get("ignore_indices"))

    @staticmethod
    def format_observation_prompt(results: dict, ignore_indices: list = None) -> str:
        prompt = "### OBSERVATIONS FROM TOOLS\n"
        
        if results.get("sql"):
            prompt += f"\n[SQL DATA]:\n{results['sql']}\n"
        
        if results.get("advisory"):
            prompt += f"\n{results['advisory']}\n"
            
        if results.get("math"):
            prompt += f"\n[MATH CALCULATIONS]:\n{results['math']}\n"

        if ignore_indices:
            prompt += f"\n[NOTE]: Ignore results at indices {ignore_indices} as per your instruction.\n"

        return prompt