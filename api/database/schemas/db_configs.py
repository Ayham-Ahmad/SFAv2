from pydantic import BaseModel, SecretStr, model_validator
from typing import Optional, Union


class SQLiteConfig(BaseModel):
    PATH: str
    TIMEOUT: int = 30


class CSVConfig(BaseModel):
    PATH: str
    DELIMITER: str = ","
    ENCODING: str = "utf-8"
    HEADER: bool = True


class PostgresConfig(BaseModel):
    HOST: str
    PORT: int = 5432
    USER: str
    PASSWORD: SecretStr
    DATABASE: str
    SSL_MODE: str = "prefer"
    CONNECT_TIMEOUT: int = 10
    STATEMENT_TIMEOUT: int = 30000
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_RECYCLE: int = 1800


class MySQLConfig(BaseModel):
    HOST: str
    PORT: int = 3306
    USER: str
    PASSWORD: SecretStr
    DATABASE: str
    CHARSET: str = "utf8mb4"
    CONNECT_TIMEOUT: int = 10
    READ_TIMEOUT: int = 30
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_RECYCLE: int = 1800


class MongoDBConfig(BaseModel):
    URI: Optional[str] = None
    HOST: Optional[str] = None
    PORT: Optional[int] = 27017
    USER: Optional[str] = None
    PASSWORD: Optional[SecretStr] = None
    DATABASE: str
    DEFAULT_COLLECTION: Optional[str] = None
    SERVER_SELECTION_TIMEOUT_MS: int = 5000

    @model_validator(mode="after")
    def validate_connection(cls, values):
        if not values.URI and not values.HOST:
            raise ValueError("Either URI or HOST must be provided")
        return values


DBConfigType = Union[
    SQLiteConfig,
    PostgresConfig,
    MySQLConfig,
    CSVConfig,
    MongoDBConfig,
]