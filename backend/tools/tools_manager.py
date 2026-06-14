import asyncio
from typing import Dict, Any
from sqlalchemy.orm import Session

from api.config import settings
from ..utils.create_tool_registry import create_tool_registry

_registry = create_tool_registry()
_tool_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TOOLS)

class ToolsManager:

    @staticmethod
    def _record_tool_step(usage_metrics: Dict[str, Any], tool_name: str):
        usage_metrics["steps"][tool_name] = usage_metrics["steps"].get(tool_name, 0) + 1
        
    @staticmethod
    async def _run_tool(tool, tool_input: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        async with _tool_semaphore:
            return await asyncio.to_thread(tool.execute, tool_input, context)

    @staticmethod
    async def main_agent_output_manager(
        db: Session,
        company_id: int,
        action_input: Dict,
        request,
        usage_metrics: Dict[str, int],
        complexity: str = "ANALYSIS",
        last_retrieval_results: Any = None,
        user_id: int = None
    ):
        if not isinstance(action_input, dict):
            return "Observation: ERROR - Action Input must be a valid JSON object.", usage_metrics, last_retrieval_results, []

        tools_input = action_input.get("tools", {}) or action_input

        context = {
            "db": db,
            "company_id": company_id,
            "request": request,
            "usage_metrics": usage_metrics,
            "retrieval_results": last_retrieval_results,
            "event_loop": asyncio.get_event_loop(),
        }

        results = {}
        generated_graphs = []

        # ── Phase 1: independent tools (retrieval, advisory) ──────────────────
        for tool_name, tool_input in tools_input.items():
            if complexity == "LOOKUP" and tool_name in ["math", "advisory"]:
                results[tool_name] = {"error": "BLOCKED: LOOKUP — use retrieval only."}
                continue
            if complexity == "COMPUTATION" and tool_name == "advisory":
                results[tool_name] = {"error": "BLOCKED: COMPUTATION — no advisory."}
                continue

            tool = _registry.get(tool_name)
            if not tool or tool.requires_retrieval:
                continue

            print(f"Phase 1: Executing tool '{tool_name}' with input: {tool_input}")

            if not tool.validate_input(tool_input):
                results[tool_name] = {"error": f"Invalid input for '{tool_name}'. Expected {tool.input_type.__name__}."}
                continue

            ToolsManager._record_tool_step(usage_metrics, tool_name)
            tool_result = await ToolsManager._run_tool(tool, tool_input, context)

            if tool_result.get("success"):
                results[tool_name] = tool_result.get("data", tool_result)
            else:
                results[tool_name] = {"error": tool_result.get("error", f"Unknown error from {tool_name}")}

            if tool_name == "retrieval" and tool_result.get("success"):
                context["retrieval_results"] = tool_result.get("data", {})
                last_retrieval_results       = context["retrieval_results"]

        # ── Phase 2: dependent tools (math, graph) ────────────────────────────
        for tool_name, tool_input in tools_input.items():
            if complexity == "LOOKUP" and tool_name in ["math", "advisory"]:
                results[tool_name] = {"error": "BLOCKED: LOOKUP — use retrieval only."}
                continue
            if complexity == "COMPUTATION" and tool_name == "advisory":
                results[tool_name] = {"error": "BLOCKED: COMPUTATION — no advisory."}
                continue

            tool = _registry.get(tool_name)
            if not tool or not tool.requires_retrieval:
                continue

            if not tool.validate_input(tool_input):
                results[tool_name] = {"error": f"Invalid input for '{tool_name}'. Expected {tool.input_type.__name__}."}
                continue

            ToolsManager._record_tool_step(usage_metrics, tool_name)
            tool_result = await ToolsManager._run_tool(tool, tool_input, context)

            if tool_result.get("success"):
                if tool_name == "graph":
                    graph_config = tool_result.get("data")
                    generated_graphs.append(graph_config)
                    results[tool_name] = "Graph generated and passed to frontend."
                else:
                    results[tool_name] = tool_result.get("data", tool_result)
            else:
                results[tool_name] = {"error": tool_result.get("error", f"Unknown error from {tool_name}")}

        return ToolsManager.format_observation_prompt(results), usage_metrics, last_retrieval_results, generated_graphs

    @staticmethod
    def format_observation_prompt(results: dict) -> str:
        if not results:
            return "Observation: No tools executed. Check Action Input format."
        prompt = "### OBSERVATIONS FROM TOOLS\n"
        for name, result in results.items():
            prompt += f"\n[{name}]:\n{result}\n"
        return prompt
