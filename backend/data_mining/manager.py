from typing import Dict, Any, Optional

from .sqlite_manager import SQLiteManager
from .csv_manager import CSVManager
from .mysql_manager import MySQLManager
from .mongo_manager import MongoManager
from .postgres_manager import PostgreSQLManager
from api.constants import DatabaseType

MANAGERS = {
    DatabaseType.SQLITE: SQLiteManager,
    DatabaseType.CSV: CSVManager,
    DatabaseType.MYSQL: MySQLManager,
    DatabaseType.MONGODB: MongoManager,
    DatabaseType.POSTGRESQL: PostgreSQLManager
}

class DataCollectionManager:
    
    @staticmethod
    def get_manager(source_type: str):
        return MANAGERS.get(source_type.lower())
    
    @staticmethod
    def get_supported_types() -> list:
        return [t.value for t in MANAGERS.keys()]
    
    @staticmethod
    def test_connection(source_type: str, config: Dict) -> Dict[str, Any]:
        manager_class = DataCollectionManager.get_manager(source_type)
        if not manager_class:
            return {
                "success": False, 
                "message": f"Unsupported data source type: {source_type}"
            }
        
        manager = manager_class(config)
        try:
            return manager.test_connection()
        finally:
            manager.disconnect()
    
    @staticmethod
    def connect(source_type: str, config: Dict) -> Optional[Any]:
        manager_class = DataCollectionManager.get_manager(source_type)
        if not manager_class:
            return None
        
        manager = manager_class(config)
        if manager.connect():
            return manager
        return None
    
    @staticmethod
    def get_schema(source_type: str, config: Dict) -> Dict[str, Any]:
        manager_class = DataCollectionManager.get_manager(source_type)
        if not manager_class:
            return {"success": False, "message": "Unsupported type"}
        
        manager = manager_class(config)
        
        try:
            if not manager.connect():
                return {"success": False, "message": "Failed to connect"}
            
            schema = manager.get_full_schema()
            return schema
        except Exception as e:
            return {"success": False, "message": f"Unexpected Error: {str(e)}"}
        finally:
            manager.disconnect()
    
    @staticmethod
    def execute_query(source_type: str, config: Dict, query: str) -> Dict[str, Any]:
        manager_class = DataCollectionManager.get_manager(source_type)
        if not manager_class:
            return {"success": False, "message": "Unsupported type"}
        
        manager = manager_class(config)
        
        try:
            if not manager.connect():
                return {"success": False, "message": "Failed to connect"}
            
            return manager.execute_query(query)
            
        except Exception as e:
            return {"success": False, "message": f"Execution Error: {str(e)}"}
        finally:
            manager.disconnect()