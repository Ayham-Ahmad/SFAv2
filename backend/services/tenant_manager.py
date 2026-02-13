from typing import Dict, Any, Optional
import sentry_sdk

from ..data_mining.manager import DataCollectionManager
from api.database.models import TentDatabase
from ..utils.encryption import decrypt_config
from ..utils.responses import create_response

class MultiTenantDBManager:
    _managers: Dict[int, Any] = {}

    @staticmethod
    def get_manager_for_tent(tent: TentDatabase) -> Optional[Any]:
        if not tent or not tent.connection_config:
            return None

        if tent.db_id in MultiTenantDBManager._managers:
            cached_manager = MultiTenantDBManager._managers[tent.db_id]

            if hasattr(cached_manager, 'is_connected') and cached_manager.is_connected:
                return cached_manager
            del MultiTenantDBManager._managers[tent.db_id]

        try:
            config = decrypt_config(tent.connection_config)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return None
        
        manager = DataCollectionManager.connect(tent.db_type, config)

        if manager:
            MultiTenantDBManager._managers[tent.db_id] = manager
            return manager

        return None
    
    @staticmethod
    def get_schema_for_tent(tent: TentDatabase) -> Dict[str, Any]:
        manager = MultiTenantDBManager.get_manager_for_tent(tent)
        if not manager:
            return MultiTenantDBManager._db_connection_failed_message()
        
        try:
            return manager.get_full_schema()
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return create_response(
                success=False,
                message="Schema retrieval failed.",
                error=str(e)
            )

    @staticmethod
    def execute_query_for_tent(tent: TentDatabase, query: str) -> Dict[str, Any]:
        manager = MultiTenantDBManager.get_manager_for_tent(tent)
        if not manager:
            return MultiTenantDBManager._db_connection_failed_message()
        
        try:
            return manager.execute_query(query)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return create_response(
                success=False,
                message="Query execution failed.",
                error=str(e)
            )
        
    @staticmethod
    def disconnect_tent(tent_id: int):
        if tent_id in MultiTenantDBManager._managers:
            manager = MultiTenantDBManager._managers[tent_id]
            try:
                manager.disconnect()
            except Exception:
                pass

            del MultiTenantDBManager._managers[tent_id]

    @staticmethod
    def test_connection_with_config(db_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        return DataCollectionManager.test_connection(db_type, config)
    
    @staticmethod
    def _db_connection_failed_message():
        return create_response(
                success=False,
                message="Could not connect to database. Check credentials or server status."
            )