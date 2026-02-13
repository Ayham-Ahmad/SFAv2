import sentry_sdk
from ..core.llm_client import call_llm
from api.constants import AIModel

def is_query_safe(user_query: str) -> bool:
    try:
        response = call_llm(user_query, model=AIModel.LLAMA_GUARD_86M, max_tokens=10)
        
        try:
            score = float(response.strip())
            return score < 0.5
        except ValueError:
            return True

    except Exception as e:
        sentry_sdk.capture_exception(e)
        return True