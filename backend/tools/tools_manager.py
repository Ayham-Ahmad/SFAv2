from sqlalchemy.orm import Session
from typing import Dict
import asyncio

from .retrieve_tool import execute_multiTent_queries
from .calculator_tool import calculate_on_multiTent_data
from .graph_tool import select_graph_template
from .advisory_tool import AdvisoryRAGTool

class ToolsManager:
    
    @staticmethod
    async def main_agent_output_manager(db: Session, company_id: int, action_input: Dict, request, usage_metrics: Dict[str, int]):
        if not isinstance(action_input, dict):
            return "Observation: ERROR - Action Input must be a valid JSON object."

        tools_input = action_input.get("tools", {})
        if not tools_input:
            tools_input = action_input

        results = {}
        
        sql_payload = tools_input.get("retrieval")
        if isinstance(sql_payload, dict):
            retrieval_result = await asyncio.to_thread(execute_multiTent_queries, db, company_id, sql_payload)
            usage_metrics["steps"]["retrieval"] += 1
            
            if retrieval_result.get("success"):
                data_dict = retrieval_result.get("data", {})
                results["retrieval"] = data_dict.get("results", {})
            else:
                results["retrieval"] = {"error": retrieval_result.get("error", "Unknown DB Error")}
            
        advisory_payload = tools_input.get("advisory")
        if isinstance(advisory_payload, list) and request:
            vector_db = getattr(request.app.state, "vector_db", None)
            usage_metrics["steps"]["advisory"] += 1
            if vector_db:
                rag_tool = AdvisoryRAGTool(vector_db)
                results["advisory"] = await asyncio.to_thread(rag_tool.get_institutional_knowledge, advisory_payload)
            else:
                results["advisory"] = "Error: Knowledge Base not initialized."

        math_payload = tools_input.get("math")
        if isinstance(math_payload, list):
            usage_metrics["steps"]["math"] += 1
            math_results = []
            for calculation in math_payload:
                query_index = calculation[0] if len(calculation) > 0 else 0
                columns = calculation[1] if len(calculation) > 1 else []
                formula = calculation[2] if len(calculation) > 2 else ""
                
                calc_res = await asyncio.to_thread(calculate_on_multiTent_data, results.get("retrieval"), formula)
                math_results.append(calc_res)
                
            results["math"] = math_results

        graph_payload = tools_input.get("graph")
        if isinstance(graph_payload, dict):
            usage_metrics["steps"]["graph"] += 1
            current_retrieval = results.get("retrieval")
            if current_retrieval and "error" not in current_retrieval:
                results["graph"] = select_graph_template(graph_payload, current_retrieval)
            else:
                results["graph"] = {"error": "Graph tool requires active retrieval data. Please call 'retrieval' in the same action."}

        return ToolsManager.format_observation_prompt(results), usage_metrics

    @staticmethod
    def format_observation_prompt(results: dict) -> str:
        if not results:
            return "Observation: No valid tools were executed. Please check your Action Input format."

        prompt = "### OBSERVATIONS FROM TOOLS\n"
        
        if results.get("retrieval"):
            prompt += f"\n[retrieval]:\n{results['retrieval']}\n"
        
        if results.get("advisory"):
            prompt += f"\n[advisory]:\n{results['advisory']}\n"
            
        if results.get("math"):
            prompt += f"\n[math]:\n{results['math']}\n"
            
        if results.get("graph"):
            prompt += f"\n[graph]:\n{results['graph']}\n"

        return prompt