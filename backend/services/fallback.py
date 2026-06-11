from typing import Dict, Any, Tuple

from api.constants import AIModel
from .prompts import FallBackPrompt
from ..core.llm_client import call_llm

class FallBackService:
    @staticmethod
    async def generate_fallback_summary(user_query: str, scratchpad: str, usage_metrics: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:

        fallback_prompt = FallBackPrompt.prompt(user_query, scratchpad)
        
        summary, usage_metrics = await call_llm(
            prompt=fallback_prompt,
            model=AIModel.LLAMA_31_8B, 
            usage_metrics=usage_metrics,
        )
        
        return summary, usage_metrics
