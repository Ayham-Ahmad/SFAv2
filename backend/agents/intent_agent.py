"""
Intent agent — classify the user query before the main reasoning loop.

Input:  user query (str)
Output: (intent_dict, updated usage_metrics)

intent_dict shape:
    {
        "intent":     "FINANCIAL" | "GREETING" | "IRRELEVANT",
        "complexity": "LOOKUP" | "COMPUTATION" | "ANALYSIS" | null,
        "confidence": 0.0-1.0,   # model's self-reported confidence
        "response":   str | null  # pre-canned reply for non-financial intents
    }

Parse strategy (most → least strict):
    1. json.loads on the first {...} block found by regex
    2. ast.literal_eval as a fallback for single-quoted JSON
    3. Hard default → FINANCIAL/ANALYSIS so the agent always continues
"""

import json
import ast
import re
import sentry_sdk
from typing import Dict, Any, Tuple

from api.constants import AIModel
from ..core.llm_client import call_llm
from ..services.prompts import IntentAgentPrompt

_DEFAULT = {"intent": "FINANCIAL", "complexity": "ANALYSIS", "confidence": 0.0, "response": None}


def _parse_response(raw: str) -> Dict[str, Any]:
    """Try to extract a JSON object from the raw LLM output."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return _DEFAULT.copy()

    candidate = match.group(0)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    try:
        result = ast.literal_eval(candidate)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    return _DEFAULT.copy()


async def classify_intent(
    user_query: str,
    usage_metrics: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:

    prompt = IntentAgentPrompt.prompt(user_query)

    try:
        response, usage_metrics = await call_llm(
            prompt,
            model=AIModel.LLAMA_31_8B,
            max_tokens=200,
            usage_metrics=usage_metrics
        )

        result = _parse_response(response)

        result.setdefault("intent", "FINANCIAL")
        result.setdefault("complexity", "ANALYSIS")
        result.setdefault("confidence", 0.0)
        result.setdefault("response", None)

        return result, usage_metrics

    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Intent agent error: {e}")
        return _DEFAULT.copy(), usage_metrics
