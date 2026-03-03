"""
This agent is to check the safety of the user query to prevent prompt injection

Input: user query
Output: Safe or not (bool), updated usage_metrics
"""

import sentry_sdk
from typing import Dict, Tuple, Any

from api.constants import AIModel
from ..core.llm_client import call_llm

async def is_query_safe(user_query: str, usage_metrics: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    try:
        response, usage_metrics = await call_llm(user_query, model=AIModel.LLAMA_GUARD_86M, max_tokens=10, usage_metrics=usage_metrics)
        
        try:
            score = float(response.strip())
            return score < 0.5, usage_metrics
        except ValueError:
            print(f"ValueError: {str(ValueError)}")
            return True, usage_metrics

    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Error: {str(e)}")
        return True, usage_metrics