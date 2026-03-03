from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, List, Any, Dict

from ...constants import CompanyPlan, GraphType, MetricFormat, PLAN_LIMITS
from .base import BaseSchema
from ...constants import AIModel
from .tents import TentStatusSchema

class TrafficLightConfig(BaseModel):
    title: str = "Financial Health"
    expression: Optional[str] = None
    green_threshold: float = 1000.0
    red_threshold: float = 0.0

class Metrics(BaseModel):
    metric_column: Optional[str] = None
    metric_format: MetricFormat = MetricFormat.CURRENCY

class GraphConfig(BaseModel):
    graph_type: GraphType = GraphType.BAR
    title: Optional[str] = "Performance Overview"
    
    x_column: Optional[str] = None
    x_format: MetricFormat = MetricFormat.TEXT
    
    y_column: Optional[str] = None
    y_format: MetricFormat = MetricFormat.CURRENCY
    
    x_secondary_column: Optional[str] = None
    x_secondary_format: MetricFormat = MetricFormat.TEXT
    
    data_range_mode: Optional[str] = "all"
    data_range_limit: Optional[int] = 12

class CompanyTentSettings(BaseModel):
    total_allowed: int = 1
    current_count: int = 0
    tents_inventory: List[TentStatusSchema] = []

class CompanyManagerSettings(BaseModel):
    total_allowed: int = 2
    current_count: int = 1

class CompanySettings(BaseModel):
    traffic_light_config: TrafficLightConfig = Field(default_factory=TrafficLightConfig)
    metrics_config: Metrics = Field(default_factory=Metrics)
    graph_config: GraphConfig = Field(default_factory=GraphConfig)
    tent_config: CompanyTentSettings = Field(default_factory=CompanyTentSettings)
    manager_config: CompanyManagerSettings = Field(default_factory=CompanyManagerSettings) # Added
    allowed_models: List[AIModel] = [] 
    
class CompanyBase(BaseSchema):
    company_name: str
    plan: CompanyPlan
    settings: CompanySettings = Field(default_factory=CompanySettings)

class CompanyCreate(BaseSchema):
    company_name: str
    plan: CompanyPlan = CompanyPlan.FREE

class CompanyUpdate(BaseSchema):
    company_name: Optional[str] = None
    plan: Optional[CompanyPlan] = None
    settings: Optional[CompanySettings] = None

class CompanyOut(CompanyBase):
    company_id: int
    databases_count: int
    managers_count: int
    company_created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def apply_plan_limits(cls, data: Any) -> Any:
        plan = getattr(data, 'plan', None) or data.get('plan')
        settings = getattr(data, 'settings', None) or data.get('settings')
        
        if plan and settings:
            limits = PLAN_LIMITS.get(plan, PLAN_LIMITS[CompanyPlan.FREE])
            
            settings.tent_config.total_allowed = limits["dbs"]
            settings.manager_config.total_allowed = limits["managers"]
            settings.allowed_models = limits["allowed_models"]
            
        return data
    
class CompanySummaryOut(BaseModel):
    company_id: int
    company_name: str
    plan: str
    managers_count: int
    databases_count: int
    company_created_at: datetime

    class Config:
        from_attributes = True

class ModelCostConfig(BaseModel):
    input_cost_per_1m: float  
    output_cost_per_1m: float 
    context_window: int 

MODEL_PRICING: Dict[AIModel, ModelCostConfig] = {
    
    # Llama 3.1 8B (Cheap & Fast)
    AIModel.LLAMA_31_8B: ModelCostConfig(
        input_cost_per_1m=0.05,   
        output_cost_per_1m=0.08,  
        context_window=131072
    ),

    # Llama 3.3 70B (Smart & Versatile)
    AIModel.LLAMA_33_70B: ModelCostConfig(
        input_cost_per_1m=0.59,   
        output_cost_per_1m=0.79,  
        context_window=131072
    ),

    # Local LLM (Free - running on your own hardware)
    AIModel.LOCAL_LLM: ModelCostConfig(
        input_cost_per_1m=0.00,
        output_cost_per_1m=0.00,
        context_window=8192
    )
}      