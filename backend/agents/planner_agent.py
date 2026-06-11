"""
Planner Agent — Multi-Hop Execution Planning

Purpose: For complex queries, creates an execution plan BEFORE the ReAct loop starts.
This decomposes complex tasks into smaller logical steps.

Paper basis: LangGraph, Plan-and-Solve, Tree-of-Thought

Input: user_query (str), tables_schema (str), usage_metrics (dict)
Output: execution_plan (str), usage_metrics (dict)
"""

import sentry_sdk
from typing import Dict, Any, Tuple

from api.constants import AIModel
from ..core.llm_client import call_llm
from ..services.prompts import PlannerAgentPrompt


async def generate_plan(
    user_query: str,
    tables_schema: str,
    usage_metrics: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Generates an execution plan for complex queries.
    """
    try:
        prompt = PlannerAgentPrompt.prompt(user_query, tables_schema)

        response, usage_metrics = await call_llm(
            prompt=prompt,
            model=AIModel.LLAMA_31_8B,  # 8B is sufficient for simple planning
            max_tokens=300,
            usage_metrics=usage_metrics
        )

        return response.strip(), usage_metrics

    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Planner error (non-blocking): {str(e)}")
        return "", usage_metrics
