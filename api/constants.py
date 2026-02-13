from enum import Enum

class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MANAGER = "manager"

class TableName(str, Enum):
    USERS = "users"
    COMPANIES = "companies"
    TENTS = "tents"

class ActionType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class AIModel(str, Enum):
    LLAMA_33_70B = r"llama-3.3-70b-versatile" 
    LLAMA_31_8B = r"llama-3.1-8b-instant" 
    LOCAL_LLM = "local-llm"
    LLAMA_GUARD_86M = r"meta-llama/llama-prompt-guard-2-86m"

class CompanyPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ULTRA = "ultra"

PLAN_LIMITS = {
    CompanyPlan.FREE: {
        "dbs": 1, 
        "managers": 2,        
        "tables": 20, 
        "storage_mb": 50,
        "allowed_models": [AIModel.LLAMA_31_8B]
    },
    CompanyPlan.PRO: {
        "dbs": 5, 
        "managers": 10, 
        "tables": 100, 
        "storage_mb": 500,
        "allowed_models": [AIModel.LLAMA_31_8B, AIModel.LLAMA_33_70B]
    },
    CompanyPlan.ULTRA: {
        "dbs": 20, 
        "managers": 50, 
        "tables": 1000, 
        "storage_mb": 5000,
        "allowed_models": [AIModel.LLAMA_31_8B, AIModel.LLAMA_33_70B, AIModel.LOCAL_LLM]
    },
}

class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    CSV = "csv"
    MONGODB = "mongodb"

class InteractionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class LlmUsageOut(str, Enum):
    COST = "cost"
    TOKENS = "tokens"
    CALLS = "calls"
    FEEDBACK = "feedback"
    ART = "avg_response_time"
    AMU = "avg_memory_usage"

class ThemesTypes(str, Enum):
    WHITE = "white"
    DARK = "dark"
    AUTO = "auto"

class Languages(str, Enum):
    ENGLISH = "en"

class GraphType(str, Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"

class MetricFormat(str, Enum):
    TEXT = "text"
    CURRENCY = "currency"
    PERCENT = "percent"
    NUMBER = "number"

FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", 
    "GRANT", "REVOKE", "CREATE", "REPLACE", "EXEC", "MERGE"
]