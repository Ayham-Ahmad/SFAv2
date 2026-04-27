from typing import Dict, Any, Optional, Tuple
import sentry_sdk
from datetime import datetime, timezone, timedelta

from ..data_mining.sqlite_manager import SQLiteManager
from ..data_mining.csv_manager import CSVManager
from ..data_mining.mysql_manager import MySQLManager
from ..data_mining.mongo_manager import MongoManager
from ..data_mining.postgres_manager import PostgreSQLManager

from api.config import settings
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
    # Stores {tent_id: (manager_instance, last_used_datetime)}
    _active_managers: Dict[int, Tuple[Any, datetime]] = {}
    
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

        # Clean up expired connections on each access
        MultiTenantDBManager._cleanup_expired()

        if tent.db_id in MultiTenantDBManager._active_managers:
            cached_manager, last_used = MultiTenantDBManager._active_managers[tent.db_id]
            
            expected_class = DB_MANAGERS.get(tent.db_type.lower())
            if isinstance(cached_manager, expected_class) and cached_manager.is_connected:
                # Update last_used timestamp
                MultiTenantDBManager._active_managers[tent.db_id] = (cached_manager, datetime.now(timezone.utc))
                return cached_manager
            
            MultiTenantDBManager.disconnect_tent(tent.db_id)

        # Evict least recently used if at capacity
        if len(MultiTenantDBManager._active_managers) >= settings.MAX_CACHED_CONNECTIONS:
            MultiTenantDBManager._evict_lru()

        try:
            config = decrypt_config(tent.connection_config)
            manager = MultiTenantDBManager._create_instance(tent.db_type, config)
            
            if manager and manager.connect():
                MultiTenantDBManager._active_managers[tent.db_id] = (manager, datetime.now(timezone.utc))
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
    def _cleanup_expired():
        """Remove connections that have been idle longer than the TTL."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=settings.CONNECTION_TTL_MINUTES)
        
        expired_ids = [
            tid for tid, (_, last_used) in MultiTenantDBManager._active_managers.items()
            if last_used < cutoff
        ]
        
        for tid in expired_ids:
            MultiTenantDBManager.disconnect_tent(tid)

    @staticmethod
    def _evict_lru():
        """Remove the least recently used connection to make room."""
        if not MultiTenantDBManager._active_managers:
            return
        
        lru_id = min(
            MultiTenantDBManager._active_managers,
            key=lambda tid: MultiTenantDBManager._active_managers[tid][1]
        )
        MultiTenantDBManager.disconnect_tent(lru_id)

    @staticmethod
    def disconnect_tent(tent_id: int):
        if tent_id in MultiTenantDBManager._active_managers:
            manager, _ = MultiTenantDBManager._active_managers[tent_id]
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