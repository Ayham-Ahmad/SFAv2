"""
This agent is to classify the type of the user query

Input: user query
Output: {intent: [FINANCIAL | GREETING | IRRELEVANT], response: return a small response if [GREETING | IRRELEVANT]}
"""

import json
import re
from typing import Dict, Any

from ..core.llm_client import call_llm
from api.constants import AIModel
from ..services.prompts import IntentAgentPrompt

def classify_intent(user_query: str) -> Dict[str, Any]:
    prompt = IntentAgentPrompt.prompt(user_query)
    
    try:
        response = call_llm(prompt, model=AIModel.LLAMA_31_8B, max_tokens=200)
        match = re.search(r"\{.*\}", response, re.DOTALL)
        
        if match:
            return json.loads(match.group(0))
        return {"intent": "FINANCIAL", "response": None}
    except Exception:
        return {"intent": "FINANCIAL", "response": None}