"""
Planner agent — multi-hop execution planning for ANALYSIS queries.

Input:  user_query, tables_schema, usage_metrics
Output: (execution_plan: str, updated usage_metrics)

Validation rule: a valid plan must contain at least one "Step" keyword.
"""

import re
import sentry_sdk
from typing import Dict, Any, Tuple

from api.constants import AIModel
from ..core.llm_client import call_llm
from ..services.prompts import PlannerAgentPrompt


def _is_valid_plan(text: str) -> bool:
    return bool(re.search(r"step\s*\d+", text, re.IGNORECASE))


async def generate_plan(
    user_query: str,
    tables_schema: str,
    usage_metrics: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:

    try:
        prompt = PlannerAgentPrompt.prompt(user_query, tables_schema)

        response, usage_metrics = await call_llm(
            prompt=prompt,
            model=AIModel.LLAMA_31_8B,
            max_tokens=300,
            usage_metrics=usage_metrics
        )

        plan = response.strip()

        if not _is_valid_plan(plan):
            print(f"Planner agent: response did not contain valid steps — skipping plan.\nRaw: {plan[:200]!r}")
            return "", usage_metrics

        return plan, usage_metrics

    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Planner agent error (non-blocking): {e}")
        return "", usage_metrics
