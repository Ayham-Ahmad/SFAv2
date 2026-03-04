import sentry_sdk
import asyncio
from fastapi import Request

from api.config import settings
from api.database.schemas import get_usage_metrics_dict
from backend.agents.SFA import SFA


async def run_task(agent: SFA, http_request: Request):
    task = asyncio.create_task(agent.main(http_request))

    try: 
        result_data, usage_metrics = await asyncio.wait_for(task, timeout=settings.TIMEOUT_SECONDS)

        if isinstance(result_data, str):
            return result_data, usage_metrics

        if isinstance(result_data, dict):
            final_answer = result_data.get("action_input", "Analysis complete, but no output provided.")
            return final_answer, usage_metrics
        
        return "Unexpected response format.", usage_metrics
    
    except asyncio.TimeoutError:
        task.cancel()
        return "The analysis took too long. Try asking for a smaller date range.", get_usage_metrics_dict()
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return f"An error occurred during analysis: {str(e)}", get_usage_metrics_dict()
