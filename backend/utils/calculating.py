import os
from typing import Dict, Any

from api.constants import AIModel
from api.database.schemas.companies import MODEL_PRICING


# def calculate_interaction_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
#     try:
#         model = AIModel(model_id)
#         rates = MODEL_PRICING.get(model)
#     except ValueError:
#         return 0.0

#     if not rates:
#         return 0.0

#     input_total = (prompt_tokens / 1_000_000) * rates.input_cost_per_1m
#     output_total = (completion_tokens / 1_000_000) * rates.output_cost_per_1m

#     return round(input_total + output_total, 6)


def calculate_csv_size_mb(csv_path) -> float:
    size_bytes = os.path.getsize(csv_path)
    return size_bytes / (1024*1024)


def extract_tokens(response: any, model: str, usage_metrics: Dict[str, Any]) -> Dict[str, Any]:
    p_tokens, c_tokens, t_tokens = 0, 0, 0

    if hasattr(response, 'response_metadata'):
        usage = response.response_metadata.get('token_usage', {})
        p_tokens = usage.get('prompt_tokens', 0)
        c_tokens = usage.get('completion_tokens', 0)
        t_tokens = usage.get('total_tokens', 0)

    elif hasattr(response, 'usage') and response.usage:
        p_tokens = getattr(response.usage, 'prompt_tokens', 0)
        c_tokens = getattr(response.usage, 'completion_tokens', 0)
        t_tokens = getattr(response.usage, 'total_tokens', 0)

    model_tokens = usage_metrics.setdefault("model_tokens", {})
    entry = model_tokens.setdefault(model, {"p_tokens": 0, "c_tokens": 0, "total_tokens": 0})
    entry["p_tokens"] += p_tokens
    entry["c_tokens"] += c_tokens
    entry["total_tokens"] += t_tokens

    return usage_metrics
