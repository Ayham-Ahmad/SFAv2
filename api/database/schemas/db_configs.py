from pydantic import BaseModel, Field
from typing import Optional, Union

class SQLiteConfig(BaseModel):
    PATH: str = Field(..., description="Full path to the .db file on the server")

class CSVConfig(BaseModel):
    PATH: str = Field(..., description="Full path to the .csv file")
    DELIMITER: str = Field(",", description="CSV delimiter (e.g., ',' or ';')")

class PostgresConfig(BaseModel):
    HOST: str
    PORT: int = 5432
    USER: str
    PASSWORD: str
    DATABASE: str
    SSL_MODE: str = "prefer" 

class MySQLConfig(BaseModel):
    HOST: str
    PORT: int = 3306
    USER: str
    PASSWORD: str
    DATABASE: str
    CHARSET: str = "utf8mb4"

class MongoDBConfig(BaseModel):
    URI: Optional[str] = None 
    
    HOST: Optional[str] = "localhost"
    PORT: int = 27017
    USER: Optional[str] = None
    PASSWORD: Optional[str] = None
    
    DATABASE: str
    DEFAULT_COLLECTION: Optional[str] = None 

DBConfigType = Union[SQLiteConfig, PostgresConfig, MySQLConfig, CSVConfig, MongoDBConfig]