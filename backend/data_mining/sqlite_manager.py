import sqlite3
import os
from typing import List, Any

from .base import BaseDataManager
from ..utils.responses import create_response

class SQLiteManager(BaseDataManager):
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.db_path = self.config.get("PATH") or self.config.get("path", "")

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def connect(self) -> bool:
        if not self.db_path or not os.path.exists(self.db_path):
            self.is_connected = False
            return False
        
        try:
            with self._get_connection() as conn:
                conn.execute("SELECT 1")
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        if not os.path.exists(self.db_path):
            return create_response(success=False, message=f"File not found: {self.db_path}")
        
        try:
            tables = self._fetch_table_names()
            return create_response(
                success=True,
                message=f"Successfully connected. Found {len(tables)} tables.",
                data={"tables": tables}
            )
        except Exception as e:
            return create_response(success=False, message="SQLite Connection Error", error=str(e))

    def _fetch_table_names(self) -> List[str]:
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]

    def get_full_schema(self) -> Any:
        try:
            tables = self._fetch_table_names()
            schema_map = {}
            
            with self._get_connection() as conn:
                for table in tables:
                    cursor = conn.execute(f"PRAGMA table_info('{table}')")
                    columns = [
                        {"name": r[1], "type": r[2], "not_null": bool(r[3]), "is_pk": bool(r[5])} 
                        for r in cursor.fetchall()
                    ]
                    
                    count_cursor = conn.execute(f"SELECT COUNT(*) FROM '{table}'")
                    rows = count_cursor.fetchone()[0]
                    
                    schema_map[table] = {
                        "columns": columns,
                        "row_count": rows
                    }
                    
            return create_response(
                success=True, 
                data={
                    "tables": tables, 
                    "schema": schema_map, 
                    "total_tables": len(tables)
                }
            )
        except Exception as e:
            return create_response(success=False, message="Failed to extract schema", error=str(e))

    def execute_query(self, query: str) -> Any:
        try:
            clean_query = query.strip().upper()
            if not clean_query.startswith("SELECT") and not clean_query.startswith("PRAGMA"):
                return create_response(
                    success=False, 
                    message="Security Violation: Only READ operations (SELECT) are allowed on tenant databases."
                )

            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row 
                cursor = conn.cursor()
                cursor.execute(query)
                
                rows = cursor.fetchall()
                data = [dict(row) for row in rows]
                
                return create_response(
                    success=True, 
                    data={
                        "columns": list(data[0].keys()) if data else [],
                        "rows": data, 
                        "row_count": len(data)
                    }
                )
        except Exception as e:
            return create_response(success=False, message="SQL Execution Error", error=str(e))

    def disconnect(self):
        self.is_connected = False