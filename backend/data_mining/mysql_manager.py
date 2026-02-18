import mysql.connector
from mysql.connector import Error
from typing import Dict, Any

from .base import BaseDataManager
from ..utils.responses import create_response


class MySQLManager(BaseDataManager):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = self.config.get("HOST")
        self.port = int(self.config.get("PORT", 3306))
        self.user = self.config.get("USER")

        pwd = self.config.get("PASSWORD")
        self.password = (
            pwd.get_secret_value() if hasattr(pwd, "get_secret_value") else pwd
        )

        self.database = self.config.get("DATABASE")
        self.charset = self.config.get("CHARSET", "utf8mb4")
        self.connect_timeout = int(self.config.get("CONNECT_TIMEOUT", 10))
        self.conn = None

    def _get_connection_params(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset,
            "connect_timeout": self.connect_timeout,
        }

    def connect(self) -> bool:
        if self.conn and self.conn.is_connected():
            return True
        
        try:
            self.conn = mysql.connector.connect(**self._get_connection_params())
            self.is_connected = self.conn.is_connected()
            return self.is_connected
        except Error as e:
            print(f"DEBUG: Connection failed: {e}")
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        try:
            if not self.connect():
                return create_response(
                    success=False, message="Failed to reach MySQL server"
                )

            db_info = self.conn.get_server_info()
            return create_response(
                success=True,
                message=f"Connected to MySQL Server version {db_info}",
                data={"version": db_info},
            )
        except Error as e:
            return create_response(
                success=False, message="MySQL Connection Error", error=str(e)
            )

    def get_full_schema(self) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        try:
            query = """
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = %s 
                ORDER BY table_name, ordinal_position;
            """

            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(query, (self.database,))
            rows = cursor.fetchall()

            schema_map = {}
            for row in rows:
                t_name = row["TABLE_NAME"]
                if t_name not in schema_map:
                    schema_map[t_name] = {"row_count": 0, "columns": []}

                column_info = f"{row['COLUMN_NAME']}: {row['DATA_TYPE']}"
                schema_map[t_name]["columns"].append(column_info)

            for t_name in schema_map.keys():
                try:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM `{t_name}`")
                    count_res = cursor.fetchone()
                    schema_map[t_name]["row_count"] = count_res["cnt"]
                except Exception:
                    schema_map[t_name]["row_count"] = -1

            cursor.close()

            return create_response(
                success=True,
                data={"total_tables": len(schema_map), "tables": schema_map},
            )

        except Exception as e:
            return create_response(
                success=False, message="MySQL Schema Extraction Failed", error=str(e)
            )

    def execute_query(self, query: str) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        clean_query = query.strip().upper()
        if not clean_query.startswith("SELECT") and not clean_query.startswith("SHOW"):
            return create_response(
                success=False, message="Security: Only READ operations allowed."
            )

        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(query)

            rows = cursor.fetchall()
            cursor.close()

            columns = list(rows[0].keys()) if rows else []

            return create_response(
                success=True,
                data={"columns": columns, "rows": rows, "row_count": len(rows)},
            )
        except Error as e:
            return create_response(
                success=False, message="Query Execution Failed", error=str(e)
            )

    def disconnect(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()
        self.is_connected = False
