import sentry_sdk
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from groq import AsyncGroq
from typing import Dict, Tuple, Optional, Any

from api.config import settings
from api.constants import AIModel
from ..utils.calculating import extract_tokens
from ..services.prompts import FallBackPrompt

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

async def call_llm(
    prompt: str, 
    model: str, 
    usage_metrics: Dict[str, Any], 
    temperature: float = 0.0, 
    max_tokens: int = 2048,
    stop: Optional[list[str]] = None
) -> Tuple[str, Dict[str, Any]]:
    try:
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if stop:
            params["stop"] = stop
            
        response = await client.chat.completions.create(**params)

        content = response.choices[0].message.content  
        if not content:
            raise ValueError("LLM returned an empty response.")
            
        extract_tokens(response, usage_metrics)
        
        usage_metrics["api_call"] += 1
        
        return content, usage_metrics
    
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return "Final Answer: I encountered a technical issue connecting to my core services. Please try again shortly.", usage_metrics
    
async def call_agent(prompt: str, model: str, usage_metrics: Dict[str, Any], user_query: str = "", scratchpad: str = "") -> Tuple[str, Dict[str, Any]]:    
    try:
        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=model,
            temperature=0.0,
            max_tokens=800,
            stop_sequences=["Observation:", "\nObservation:"]
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        usage_metrics["api_call"] += 1
                        
        return response.content, usage_metrics

    except Exception as e:
        error_msg = str(e).lower()
        sentry_sdk.capture_exception(e)
        print(f"Error, using Fallback model: {error_msg}")
        
        is_limit_error = any(x in error_msg for x in ["429", "rate_limit", "rate limit", "tokens_per_day", "limit_exceeded"])
        
        if is_limit_error:
            sentry_sdk.capture_message("[SFA Agent] API limit hit - using fallback model", level="info")
                        
            return await call_llm(
                prompt=FallBackPrompt.prompt(user_query, scratchpad), 
                model=AIModel.LLAMA_31_8B, 
                usage_metrics=usage_metrics, 
                max_tokens=800,
                stop=["Observation:", "\nObservation:"]
            )
                
        return "Final Answer: I could not process that request. Please try again.", usage_metrics