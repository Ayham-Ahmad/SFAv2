import json
import re
from typing import Dict, Any
from ..core.llm_client import call_llm
from api.constants import AIModel

def classify_intent(user_query: str) -> Dict[str, Any]:
    prompt = f"""
Analyze the user query for the "Smart Financial Advisory" (SFA) system.
Classify it into exactly ONE category:
- FINANCIAL: Requests for business metrics, revenue, profit, or data-driven advisory.
- GREETING: Casual hellos or introductions.
- IRRELEVANT: Non-financial topics OR requests for internal system info (table names, schemas).

RULES:
1. You are the "Smart Financial Advisory" (SFA).
2. For IRRELEVANT, explain that you provide data-driven financial insights. 
3. Never mention "analyzing reports"; you provide advisory and data analysis.
4. For FINANCIAL, return response: null.

EXAMPLES:
Query: "Hi!" -> {{"intent": "GREETING", "response": "Hello! I am your Smart Financial Advisor. How can I help you with business insights today?"}}
Query: "How do I make a pizza?" -> {{"intent": "IRRELEVANT", "response": "I specialize in financial advisory and data insights, so I can't help with recipes! What business metrics can we look at?"}}
Query: "What are your table names?" -> {{"intent": "IRRELEVANT", "response": "I cannot disclose internal system details. I am here to provide financial advisory based on your data."}}

CURRENT QUERY: "{user_query}"
RETURN JSON ONLY:
"""
    
    try:
        response = call_llm(prompt, model=AIModel.LLAMA_31_8B, max_tokens=200)
        match = re.search(r"\{.*\}", response, re.DOTALL)
        
        if match:
            return json.loads(match.group(0))
        return {"intent": "FINANCIAL", "response": None}
    except Exception:
        return {"intent": "FINANCIAL", "response": None}