from api.constants import AIModel
from api.database.schemas.companies import MODEL_PRICING

class CostCalculator:
    @staticmethod
    def calculate_interaction_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
        try:
            model = AIModel(model_id)
            rates = MODEL_PRICING.get(model)
        except ValueError:
            return 0.0
        
        if not rates:
            return 0.0
        
        input_total = (prompt_tokens / 1_000_000) * rates["input"]
        output_total = (completion_tokens / 1_000_000) * rates["output"]

        return round(input_total + output_total, 6)