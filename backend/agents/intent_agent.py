"""
This agent is to classify the type of the user query

Input: user query
Output: {intent: [FINANCIAL | GREETING | IRRELEVANT], response: return a small response if [GREETING | IRRELEVANT]}, updated usage_metrics
"""

import json
import re
import sentry_sdk
from typing import Dict, Any, Tuple

from api.constants import AIModel
from ..core.llm_client import call_llm
from ..services.prompts import IntentAgentPrompt

async def classify_intent(user_query: str, usage_metrics: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    prompt = IntentAgentPrompt.prompt(user_query)
    
    try:
        response, usage_metrics = await call_llm(prompt, model=AIModel.LLAMA_31_8B, max_tokens=200, usage_metrics=usage_metrics)
        match = re.search(r"\{.*\}", response, re.DOTALL)
        
        if match:
            return json.loads(match.group(0)), usage_metrics
        return {"intent": "FINANCIAL", "response": None}, usage_metrics
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Error: {str(e)}")
        return {"intent": "FINANCIAL", "response": None}, usage_metrics