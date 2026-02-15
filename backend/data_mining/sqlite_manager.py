import sqlite3
import os
from typing import Dict, Any

from .base import BaseDataManager
from ..utils.responses import create_response


class SQLiteManager(BaseDataManager):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_path = self.config.get("PATH") or self.config.get("path")
        self.timeout = int(self.config.get("TIMEOUT", 30))
        self.conn = None

    def connect(self) -> bool:
        if self.conn:
            return True

        if not self.db_path or not os.path.exists(self.db_path):
            self.is_connected = False
            return False

        try:
            self.conn = sqlite3.connect(
                self.db_path, timeout=self.timeout, check_same_thread=False
            )
            self.conn.row_factory = sqlite3.Row

            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()

            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        if not self.db_path or not os.path.exists(self.db_path):
            return create_response(
                success=False, message=f"File not found: {self.db_path}"
            )

        try:
            if not self.connect():
                return create_response(
                    success=False, message="Failed to connect to SQLite DB"
                )

            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()

            return create_response(
                success=True,
                message=f"Successfully connected. Found {len(tables)} tables.",
                data={"tables": tables},
            )
        except Exception as e:
            return create_response(
                success=False, message="SQLite Connection Error", error=str(e)
            )

    def get_full_schema(self) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            table_names = [row[0] for row in cursor.fetchall()]

            schema_map = {}

            for table in table_names:
                cursor.execute(f"PRAGMA table_info('{table}')")
                columns = [f"{r['name']}: {r['type']}" for r in cursor.fetchall()]

                cursor.execute(f"SELECT COUNT(*) FROM '{table}'")
                row_count = cursor.fetchone()[0]

                schema_map[table] = {"row_count": row_count, "columns": columns}

            cursor.close()
            return create_response(
                success=True,
                data={"total_tables": len(table_names), "tables": schema_map},
            )
        except Exception as e:
            return create_response(
                success=False, message="SQLite Schema Error", error=str(e)
            )

    def execute_query(self, query: str) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        clean_query = query.strip().upper()
        if not clean_query.startswith("SELECT") and not clean_query.startswith(
            "PRAGMA"
        ):
            return create_response(
                success=False, message="Security: Only READ operations allowed."
            )

        try:
            cursor = self.conn.cursor()
            cursor.execute(query)

            rows = cursor.fetchall()
            cursor.close()

            data = [dict(row) for row in rows]
            columns = list(data[0].keys()) if data else []

            return create_response(
                success=True,
                data={"columns": columns, "rows": data, "row_count": len(data)},
            )
        except Exception as e:
            return create_response(
                success=False, message="Query Execution Failed", error=str(e)
            )

    def disconnect(self):
        if self.conn:
            self.conn.close()
        self.is_connected = False
