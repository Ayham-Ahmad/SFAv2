import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class StaticSettings(BaseSettings):
    ALGORITHM:                  str   = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int  = 1440
    DATABASE_URL:               str   = "sqlite:///./api/database/data/sfa_database.db"
    TIMEOUT_SECONDS:            int   = 180
    ROW_LIMIT:                  int   = 20
    MAX_GRAPHS:                 int   = 2
    CONNECTION_TTL_MINUTES:     int   = 30
    MAX_CACHED_CONNECTIONS:     int   = 100
    MAX_ITERATIONS:             int   = 10
    MAX_SCRATCHPAD_CHARS:       int   = 12000
    VERIFIER_SCRATCHPAD_CHARS:  int   = 6000
    GUARD_SCORE_THRESHOLD:      float = 0.5
    CHAT_MESSAGE_MAX_LENGTH:    int   = 2000
    MAX_CONCURRENT_TOOLS:       int   = 4
    ADMIN_PAGE_MAX_LIMIT:       int   = 100
    RESET_TOKEN_EXPIRE_MINUTES: int   = 30
    FRONTEND_URL:               str   = "http://localhost:8000"
    SMTP_HOST:                  str   = "localhost"
    SMTP_PORT:                  int   = 1025
    SMTP_TLS:                   bool  = False
    SMTP_FROM:                  str   = "noreply@sfa.local"
    SMTP_USER:                  str   = ""
    SMTP_PASSWORD:              str   = ""

class EnvSettings(BaseSettings):
    SECRET_KEY:        str = Field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    DB_ENCRYPTION_KEY: str = Field(default_factory=lambda: os.getenv("DB_ENCRYPTION_KEY", ""))
    SENTRY_SDK_DNS:    str = Field(default_factory=lambda: os.getenv("SENTRY_SDK_DNS", ""))
    GROQ_API_KEY:      str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    OPENAI_API_KEY:    str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SECRET_KEY:
            raise ValueError("CRITICAL ERROR: 'SECRET_KEY' not found in .env file.")
        if not self.DB_ENCRYPTION_KEY:
            raise ValueError("CRITICAL ERROR: 'DB_ENCRYPTION_KEY' not found in .env file.")


class UnifiedSettings(StaticSettings, EnvSettings):
    def __init__(self, **kwargs):
        StaticSettings.__init__(self, **kwargs)
        EnvSettings.__init__(self, **kwargs)


settings = UnifiedSettings()

if settings.DATABASE_URL.startswith("sqlite"):
    db_path_str = settings.DATABASE_URL.replace("sqlite:///", "")
    db_folder   = Path(db_path_str).parent
    if not db_folder.exists():
        db_folder.mkdir(parents=True, exist_ok=True)
        print(f"--- Environment Setup: Created directory {db_folder} ---")