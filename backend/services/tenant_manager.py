import sentry_sdk
import asyncio
from typing import Dict, Any, Optional, Tuple
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
    ### {tent_id: (manager_instance, last_used_datetime)}
    _active_managers: Dict[int, Tuple[Any, datetime]] = {}
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @staticmethod
    def get_supported_types() -> list:
        return [t.value for t in DB_MANAGERS.keys()]

    @staticmethod
    def _create_instance(db_type: str, config: Dict[str, Any]) -> Optional[Any]:
        manager_class = DB_MANAGERS.get(db_type.lower())
        return manager_class(config) if manager_class else None

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
    async def get_manager_for_tent(tent: TentDatabase) -> Optional[Any]:
        if not tent or not tent.connection_config:
            return None

        lock = MultiTenantDBManager._get_lock()
        async with lock:
            MultiTenantDBManager._cleanup_expired_unsafe()

            cached = MultiTenantDBManager._active_managers.get(tent.db_id)
            if cached:
                cached_manager, _ = cached
                expected_class = DB_MANAGERS.get(tent.db_type.lower())
                if isinstance(cached_manager, expected_class) and cached_manager.is_connected:
                    if cached_manager.connect():
                        MultiTenantDBManager._active_managers[tent.db_id] = (
                            cached_manager, datetime.now(timezone.utc)
                        )
                        return cached_manager
                MultiTenantDBManager._disconnect_unsafe(tent.db_id)

            if len(MultiTenantDBManager._active_managers) >= settings.MAX_CACHED_CONNECTIONS:
                MultiTenantDBManager._evict_lru_unsafe()

            try:
                config = decrypt_config(tent.connection_config)
                manager = MultiTenantDBManager._create_instance(tent.db_type, config)
                if manager and manager.connect():
                    MultiTenantDBManager._active_managers[tent.db_id] = (
                        manager, datetime.now(timezone.utc)
                    )
                    return manager
            except Exception as e:
                sentry_sdk.capture_exception(e)

        return None

    @staticmethod
    async def get_schema_for_tent(tent: TentDatabase) -> Dict[str, Any]:
        manager = await MultiTenantDBManager.get_manager_for_tent(tent)
        if not manager:
            return MultiTenantDBManager._connection_failed()
        try:
            schema = manager.get_full_schema()
            if schema and schema.get("success"):
                tent.last_synced = datetime.now(timezone.utc)
                tent.last_ping  = datetime.now(timezone.utc)
            return schema
        except Exception as e:
            await MultiTenantDBManager.disconnect_tent(tent.db_id)
            sentry_sdk.capture_exception(e)
            return create_response(False, "Schema retrieval failed.", error=str(e))

    @staticmethod
    async def execute_query_for_tent(tent: TentDatabase, query: str) -> Dict[str, Any]:
        manager = await MultiTenantDBManager.get_manager_for_tent(tent)
        if not manager:
            return MultiTenantDBManager._connection_failed()
        try:
            return manager.execute_query(query)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return create_response(False, "Query failed", error=str(e))

    @staticmethod
    async def disconnect_tent(tent_id: int):
        lock = MultiTenantDBManager._get_lock()
        async with lock:
            MultiTenantDBManager._disconnect_unsafe(tent_id)

    # ── private helpers — always called while holding the lock ───────────────

    @staticmethod
    def _cleanup_expired_unsafe():
        now    = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=settings.CONNECTION_TTL_MINUTES)
        expired = [
            tid for tid, (_, lu) in MultiTenantDBManager._active_managers.items()
            if lu < cutoff
        ]
        for tid in expired:
            MultiTenantDBManager._disconnect_unsafe(tid)

    @staticmethod
    def _evict_lru_unsafe():
        if not MultiTenantDBManager._active_managers:
            return
        lru_id = min(
            MultiTenantDBManager._active_managers,
            key=lambda tid: MultiTenantDBManager._active_managers[tid][1]
        )
        MultiTenantDBManager._disconnect_unsafe(lru_id)

    @staticmethod
    def _disconnect_unsafe(tent_id: int):
        entry = MultiTenantDBManager._active_managers.pop(tent_id, None)
        if entry:
            try:
                entry[0].disconnect()
            except Exception:
                pass

    @staticmethod
    def _connection_failed() -> Dict[str, Any]:
        return create_response(
            success=False,
            message="Could not connect to database. Check credentials or server status.",
        )