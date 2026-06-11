import asyncio
from typing import Dict, Any
from sqlalchemy.orm import Session

from ..utils.create_tool_registry import create_tool_registry
from api.database.events.graphs_events import GraphsCRUD

_registry = create_tool_registry()

class ToolsManager:

    @staticmethod
    def _record_tool_step(usage_metrics: Dict[str, Any], tool_name: str):
        usage_metrics["steps"][tool_name] = usage_metrics["steps"].get(tool_name, 0) + 1

    @staticmethod
    async def main_agent_output_manager(db: Session, company_id: int, action_input: Dict, request, usage_metrics: Dict[str, int], complexity: str = "ANALYSIS", last_retrieval_results: Any = None, user_id: int = None):
        if not isinstance(action_input, dict):
            return "Observation: ERROR - Action Input must be a valid JSON object.", usage_metrics, last_retrieval_results, []

        tools_input = action_input.get("tools", {})
        if not tools_input:
            tools_input = action_input

        context = {
            "db": db,
            "company_id": company_id,
            "request": request,
            "usage_metrics": usage_metrics,
            "retrieval_results": last_retrieval_results,
        }

        results = {}
        generated_graphs = []

        # Phase 1: Execute INDEPENDENT tools (retrieval, advisory)
        for tool_name, tool_input in tools_input.items():
            
            # STATE-MACHINE ROUTING MIDDLEWARE (Gap 5: externalizing logic from prompts)
            if complexity == "LOOKUP" and tool_name in ["math", "advisory"]:
                results[tool_name] = {"error": f"BLOCKED BY SYSTEM ROUTER: Complexity is LOOKUP. You are only permitted to use 'retrieval' or 'graph'."}
                continue
            if complexity == "COMPUTATION" and tool_name == "advisory":
                results[tool_name] = {"error": f"BLOCKED BY SYSTEM ROUTER: Complexity is COMPUTATION. You are only permitted to use 'retrieval', 'math', or 'graph'."}
                continue

            tool = _registry.get(tool_name)

            if not tool or tool.requires_retrieval:
                continue  # Skip dependent tools — they run in Phase 2

            print(f"Phase 1: Executing tool '{tool_name}' with input: {tool_input}")

            if not tool.validate_input(tool_input):
                results[tool_name] = {"error": f"Invalid input type for '{tool_name}'. Expected {tool.input_type.__name__}."}
                continue

            ToolsManager._record_tool_step(usage_metrics, tool_name)

            tool_result = await asyncio.to_thread(tool.execute, tool_input, context)

            # Store result
            if tool_result.get("success"):
                results[tool_name] = tool_result.get("data", tool_result)
            else:
                results[tool_name] = {"error": tool_result.get("error", f"Unknown error from {tool_name} while executing")}

            # If this was retrieval, share results with dependent tools and update state (last_retrieval_results) variable
            if tool_name == "retrieval" and tool_result.get("success"):
                context["retrieval_results"] = tool_result.get("data", {})
                last_retrieval_results = context["retrieval_results"]

        # Phase 2: Execute DEPENDENT tools (math, graph)
        for tool_name, tool_input in tools_input.items():
            
            # STATE-MACHINE ROUTING MIDDLEWARE (Gap 5: externalizing logic from prompts)
            if complexity == "LOOKUP" and tool_name in ["math", "advisory"]:
                results[tool_name] = {"error": f"BLOCKED BY SYSTEM ROUTER: Complexity is LOOKUP. You are only permitted to use 'retrieval' or 'graph'."}
                continue
            if complexity == "COMPUTATION" and tool_name == "advisory":
                results[tool_name] = {"error": f"BLOCKED BY SYSTEM ROUTER: Complexity is COMPUTATION. You are only permitted to use 'retrieval', 'math', or 'graph'."}
                continue

            tool = _registry.get(tool_name)

            if not tool or not tool.requires_retrieval:
                continue  # Already handled in Phase 1

            print(f"Phase 2: Executing tool '{tool_name}' with input: {tool_input}")

            if not tool.validate_input(tool_input):
                results[tool_name] = {"error": f"Invalid input type for '{tool_name}'. Expected {tool.input_type.__name__}."}
                continue

            ToolsManager._record_tool_step(usage_metrics, tool_name)

            tool_result = await asyncio.to_thread(tool.execute, tool_input, context) # excute the tools

            if tool_result.get("success"):
                if tool_name == "graph":
                    graph_config = tool_result.get("data")
                    generated_graphs.append(graph_config)
                    # GraphsCRUD.create(db, graph_config, user_id) # Temporarily disabled
                    results[tool_name] = "Graph successfully generated and passed to the frontend. You may now output your Final Answer and tell the user."
                else:
                    results[tool_name] = tool_result.get("data", tool_result)
            else:
                results[tool_name] = {"error": tool_result.get("error", f"Unknown error from {tool_name}")}

        return ToolsManager.format_observation_prompt(results), usage_metrics, last_retrieval_results, generated_graphs

    @staticmethod
    def format_observation_prompt(results: dict) -> str:
        if not results:
            return "Observation: No valid tools were executed. Please check your Action Input format."

        prompt = "### OBSERVATIONS FROM TOOLS\n"

        for tool_name, tool_result in results.items():
            prompt += f"\n[{tool_name}]:\n{tool_result}\n"

        return prompt