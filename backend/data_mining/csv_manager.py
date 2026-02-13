import os
import csv
import sqlite3
import tempfile
import uuid
from typing import Dict, Any

from .base import BaseDataManager
from .sqlite_manager import SQLiteManager
from ..utils.responses import create_response

class CSVManager(BaseDataManager):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.csv_path = self.config.get("PATH") or self.config.get("path", "")
        
        self.delimiter = self.config.get("DELIMITER") or self.config.get("delimiter", ",")
        
        self.temp_db_path = None
        self.table_name = self._generate_table_name()
        self.sqlite_engine = None

    def _generate_table_name(self) -> str:
        base = os.path.splitext(os.path.basename(self.csv_path))[0]
        return base.strip().replace(" ", "_").replace("-", "_").replace(".", "_")

    def connect(self) -> bool:
        if not self.csv_path or not os.path.exists(self.csv_path):
            return False

        try:
            temp_dir = tempfile.gettempdir()
            self.temp_db_path = os.path.join(temp_dir, f"sfa_csv_{uuid.uuid4().hex[:8]}.db")
            
            with open(self.csv_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                headers = [h.strip().replace(" ", "_") for h in next(reader)]
                
                with sqlite3.connect(self.temp_db_path) as conn:
                    cols_def = ", ".join([f'"{h}" TEXT' for h in headers])
                    conn.execute(f'CREATE TABLE "{self.table_name}" ({cols_def})')
                    
                    placeholders = ", ".join(["?" for _ in headers])
                    conn.executemany(f'INSERT INTO "{self.table_name}" VALUES ({placeholders})', reader)
                    conn.commit()

            self.sqlite_engine = SQLiteManager({"path": self.temp_db_path})
            self.is_connected = self.sqlite_engine.connect()
            return self.is_connected
        except Exception:
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        if not os.path.exists(self.csv_path):
            return create_response(success=False, message=f"CSV file not found")
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                headers = next(reader)
                return create_response(
                    success=True,
                    message=f"CSV Valid. {len(headers)} columns detected.",
                    data={"table": self.table_name, "headers": headers}
                )
        except Exception as e:
            return create_response(success=False, message="CSV Read Error", error=str(e))

    def get_full_schema(self) -> Any:
        if not self.is_connected and not self.connect():
            return create_response(success=False, message="Failed to process CSV")
        return self.sqlite_engine.get_full_schema()

    def execute_query(self, query: str) -> Any:
        if not self.is_connected and not self.connect():
            return create_response(success=False, message="No active CSV connection")
        
        if not query.strip().upper().startswith("SELECT"):
            return create_response(success=False, message="Security: Only SELECT queries allowed.")
            
        return self.sqlite_engine.execute_query(query)

    def disconnect(self):
        self.is_connected = False
        if self.sqlite_engine:
            self.sqlite_engine.disconnect()
        
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass