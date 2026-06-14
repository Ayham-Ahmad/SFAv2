"""
This agent is to check the safety of the user query to prevent prompt injection

Input: user query
Output: Safe or not (bool), updated usage_metrics
"""

import sentry_sdk
from typing import Dict, Tuple, Any

from api.config import settings
from api.constants import AIModel
from ..core.llm_client import call_llm


async def is_query_safe(user_query: str, usage_metrics: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    try:
        response, usage_metrics = await call_llm(
            user_query,
            model=AIModel.LLAMA_GUARD_86M,
            max_tokens=10,
            usage_metrics=usage_metrics
        )

        try:
            score = float(response.strip())
            is_safe = score < settings.GUARD_SCORE_THRESHOLD
            return is_safe, usage_metrics
        except ValueError as e:
            sentry_sdk.capture_message(
                f"Guard agent returned non-numeric score: {response!r} — {e}",
                level="warning"
            )
            return True, usage_metrics

    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Guard agent error: {e}")
        return True, usage_metrics