import os
import csv
import sqlite3
import tempfile
import uuid
from typing import Dict, Any, Optional

from .base import BaseDataManager
from .sqlite_manager import SQLiteManager
from ..utils.responses import create_response
from ..utils.calculating import calculate_csv_size_mb


class CSVManager(BaseDataManager):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.csv_path = self.config.get("PATH") or self.config.get("path")
        self.delimiter = self.config.get("DELIMITER") or self.config.get("delimiter", ",")
        self.encoding = self.config.get("ENCODING") or self.config.get("encoding", "utf-8")
        self.has_header = self.config.get("HEADER", True)

        self.temp_db_path: Optional[str] = None
        self.table_name = self._generate_table_name()
        self.sqlite_engine: Optional[SQLiteManager] = None

    def _generate_table_name(self) -> str:
        if not self.csv_path:
            return "csv_table"
        base = os.path.splitext(os.path.basename(self.csv_path))[0]
        return base.strip().replace(" ", "_").replace("-", "_").replace(".", "_")

    def connect(self) -> bool:
        if self.sqlite_engine and self.temp_db_path:
            if self.sqlite_engine.db_path == self.temp_db_path and self.sqlite_engine.connect():
                self.is_connected = True
                return True

        if not self.csv_path or not os.path.exists(self.csv_path):
            self.is_connected = False
            return False

        try:
            temp_dir = tempfile.gettempdir()
            self.temp_db_path = os.path.join(
                temp_dir, f"sfa_csv_{uuid.uuid4().hex[:8]}.db"
            )

            with open(self.csv_path, "r", encoding=self.encoding, newline="") as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                try:
                    headers = next(reader)
                except StopIteration:
                    self.is_connected = False
                    return False

                sanitized_headers = []
                for i, h in enumerate(headers):
                    clean_name = h.strip().replace(" ", "_").replace(".", "_").replace("-", "_")
                    
                    if not clean_name:
                        clean_name = "id" if i == 0 else f"column_{i}"
                    
                    sanitized_headers.append(clean_name)

                with sqlite3.connect(self.temp_db_path) as conn:
                    cols_def = ", ".join([f'"{h}" TEXT' for h in sanitized_headers])
                    conn.execute(f'CREATE TABLE "{self.table_name}" ({cols_def})')
                    
                    placeholders = ", ".join(["?" for _ in sanitized_headers])
                    insert_query = f'INSERT INTO "{self.table_name}" VALUES ({placeholders})'
                    
                    conn.executemany(insert_query, reader)
                    conn.commit()

            self.sqlite_engine = SQLiteManager({"PATH": self.temp_db_path})
            if self.sqlite_engine.connect():
                self.is_connected = True
                return True

            self.is_connected = False
            return False

        except Exception as e:
            print(f"DEBUG: CSV connect error: {str(e)}")
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        if not self.csv_path or not os.path.exists(self.csv_path):
            return create_response(success=False, message="CSV file not found")

        try:
            with open(self.csv_path, "r", encoding=self.encoding) as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                headers = next(reader)

            return create_response(
                success=True,
                message=f"CSV Valid. {len(headers)} columns detected.",
                data={"table": self.table_name, "headers": headers},
            )
        except Exception as e:
            return create_response(
                success=False, message="CSV Read Error", error=str(e)
            )

    def get_full_schema(self) -> Any:
        if not self.connect() or not self.sqlite_engine:
            return create_response(
                success=False, message="Failed to process CSV - Engine not initialized"
            )
            
        try:
            response = self.sqlite_engine.get_full_schema(include_samples=True)
        except Exception as e:
            print(f"DEBUG: SQLite engine schema error: {str(e)}")
            return create_response(
                success=False, 
                message="Internal SQLite error during schema extraction", 
                error=str(e)
            )

        if response.get("success"):
            size_mb = calculate_csv_size_mb(self.csv_path)
            response["data"]["total_size_mb"] = round(size_mb, 2)
            return response

        return create_response(
            success=False,
            message="CSV Schema Extraction Failed",
            error=response.get("message"),
        )

    def execute_query(self, query: str) -> Any:
        if not self.connect() or not self.sqlite_engine:
            return create_response(success=False, message="No active CSV connection")

        clean_query = query.strip().upper()
        if not clean_query.startswith("SELECT"):
            return create_response(
                success=False, message="Security: Only SELECT queries allowed."
            )

        return self.sqlite_engine.execute_query(query)

    def disconnect(self):
        self.is_connected = False
        if self.sqlite_engine:
            self.sqlite_engine.disconnect()
            self.sqlite_engine = None

        if self.temp_db_path and os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass
        self.temp_db_path = None
