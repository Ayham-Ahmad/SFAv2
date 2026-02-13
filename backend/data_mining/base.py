from abc import ABC, abstractmethod
from typing import Dict, Any, Union
from pydantic import BaseModel

class BaseDataManager(ABC):
    def __init__(self, config: Union[Dict[str, Any], BaseModel]):
        if isinstance(config, BaseModel):
            self.config = config.model_dump()
        else:
            self.config = config
            
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def test_connection(self) -> Any:
        pass

    @abstractmethod
    def get_full_schema(self) -> Any:
        pass

    @abstractmethod
    def execute_query(self, query: str) -> Any:
        pass

    @abstractmethod
    def disconnect(self):
        pass