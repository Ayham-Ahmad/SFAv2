from typing import Dict, Any, Optional
import sentry_sdk
from datetime import datetime, timezone

from ..data_mining.sqlite_manager import SQLiteManager
from ..data_mining.csv_manager import CSVManager
from ..data_mining.mysql_manager import MySQLManager
from ..data_mining.mongo_manager import MongoManager
from ..data_mining.postgres_manager import PostgreSQLManager

from api.constants import DatabaseType
from api.database.models import TentDatabase
from ..utils.encryption import decrypt_config
from ..utils.responses import create_response

DB_MANAGERS = {
    DatabaseType.SQLITE: SQLiteManager,
    DatabaseType.CSV: CSVManager,
    DatabaseType.MYSQL: MySQLManager,
    DatabaseType.MONGODB: MongoManager,
    DatabaseType.POSTGRESQL: PostgreSQLManager
}

class MultiTenantDBManager:
    _active_managers: Dict[int, Any] = {}
    
    @staticmethod
    def get_supported_types() -> list:
        return [t.value for t in DB_MANAGERS.keys()]

    @staticmethod
    def _create_instance(db_type: str, config: Dict[str, Any]) -> Optional[Any]:
        manager_class = DB_MANAGERS.get(db_type.lower())
        if not manager_class:
            return None
        return manager_class(config)

    @staticmethod
    def test_connection_with_config(db_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        manager = MultiTenantDBManager._create_instance(db_type, config)
        if not manager:
             return create_response(False, f"Unsupported DB Type: {db_type}")
        
        try:
            return manager.test_connection()
        finally:
            manager.disconnect()

    @staticmethod
    def get_manager_for_tent(tent: TentDatabase) -> Optional[Any]:
        if not tent or not tent.connection_config:
            return None

        if tent.db_id in MultiTenantDBManager._active_managers:
            cached = MultiTenantDBManager._active_managers[tent.db_id]
            
            expected_class = DB_MANAGERS.get(tent.db_type.lower())
            if isinstance(cached, expected_class) and cached.is_connected:
                return cached
            
            MultiTenantDBManager.disconnect_tent(tent.db_id)

        try:
            config = decrypt_config(tent.connection_config)
            manager = MultiTenantDBManager._create_instance(tent.db_type, config)
            
            if manager and manager.connect():
                MultiTenantDBManager._active_managers[tent.db_id] = manager
                return manager
        except Exception as e:
            sentry_sdk.capture_exception(e)
        
        return None

    @staticmethod
    def get_schema_for_tent(tent: TentDatabase) -> Dict[str, Any]:
        manager = MultiTenantDBManager.get_manager_for_tent(tent)
        if not manager:
            return MultiTenantDBManager._db_connection_failed_message()

        try:
            
            schema = manager.get_full_schema()

            if schema and schema.get("success"):
                tent.last_synced = datetime.now(timezone.utc)
                tent.last_ping = datetime.now(timezone.utc)
            return schema
        except Exception as e:
            print(str(e))
            MultiTenantDBManager.disconnect_tent(tent.db_id)
            sentry_sdk.capture_exception(e)
            return create_response(False, "Schema retrieval failed.", error=str(e))

    @staticmethod
    def execute_query_for_tent(tent: TentDatabase, query: str) -> Dict[str, Any]:
        manager = MultiTenantDBManager.get_manager_for_tent(tent)
        if not manager:
            return MultiTenantDBManager._db_connection_failed_message()
        try:
            return manager.execute_query(query)
        except Exception as e:
            return create_response(False, "Query failed", error=str(e))

    @staticmethod
    def disconnect_tent(tent_id: int):
        if tent_id in MultiTenantDBManager._active_managers:
            manager = MultiTenantDBManager._active_managers[tent_id]
            try:
                manager.disconnect()
            except Exception:
                pass
            del MultiTenantDBManager._active_managers[tent_id]

    @staticmethod
    def _db_connection_failed_message():
        return create_response(
            success=False,
            message="Could not connect to database. Check credentials or server status.",
        )