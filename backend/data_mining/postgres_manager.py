import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any

from .base import BaseDataManager
from ..utils.responses import create_response


class PostgreSQLManager(BaseDataManager):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = self.config.get("HOST") or self.config.get("host")
        self.port = self.config.get("PORT") or self.config.get("port", 5432)
        self.user = self.config.get("USER") or self.config.get("user")

        pwd = self.config.get("PASSWORD") or self.config.get("password")
        self.password = pwd.get_secret_value() if hasattr(pwd, "get_secret_value") else pwd

        self.database = self.config.get("DATABASE") or self.config.get("database")
        self.ssl_mode = self.config.get("SSL_MODE") or self.config.get("ssl_mode", "prefer")
        self.conn = None

    def _get_connection_params(self):
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "dbname": self.database,
            "sslmode": self.ssl_mode,
            "connect_timeout": 5
        }

    def connect(self) -> bool:
        try:
            if self.conn and not self.conn.closed:
                return True

            self.conn = psycopg2.connect(**self._get_connection_params())
            self.is_connected = True
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        try:
            if not self.connect():
                return create_response(
                    success=False, message="Failed to establish connection"
                )

            with self.conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]

            return create_response(
                success=True,
                message=f"Connected successfully. Server: {version}",
                data={"version": version},
            )
        except Exception as e:
            return create_response(
                success=False, message="Connection Error", error=str(e)
            )

    def get_full_schema(self) -> Any:
        if not self.connect():
            return create_response(success=False, message="Not connected to database")

        try:
            schema_query = """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """

            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(schema_query)
                rows = cursor.fetchall()

            schema_map = {}
            tables_list = []

            for row in rows:
                t_name = row["table_name"]
                if t_name not in schema_map:
                    schema_map[t_name] = {"columns": [], "row_count": 0}
                    tables_list.append(t_name)

                schema_map[t_name]["columns"].append(
                    {
                        "name": row["column_name"],
                        "type": row["data_type"],
                        "nullable": row["is_nullable"] == "YES",
                    }
                )

            with self.conn.cursor() as cursor:
                for t in tables_list:
                    cursor.execute(f"SELECT COUNT(*) FROM {t}")
                    schema_map[t]["row_count"] = cursor.fetchone()[0]

            return create_response(
                success=True,
                data={
                    "tables": tables_list,
                    "schema": schema_map,
                    "total_tables": len(tables_list),
                },
            )

        except Exception as e:
            return create_response(
                success=False, message="Schema Extraction Failed", error=str(e)
            )

    def execute_query(self, query: str) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        clean_query = query.strip().upper()
        if not clean_query.startswith("SELECT"):
            return create_response(
                success=False, message="Security: Only SELECT queries allowed."
            )

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

                data = [dict(row) for row in rows]
                columns = list(data[0].keys()) if data else []

                return create_response(
                    success=True,
                    data={"columns": columns, "rows": data, "row_count": len(data)},
                )
        except Exception as e:
            self.conn.rollback()
            return create_response(
                success=False, message="Query Execution Failed", error=str(e)
            )

    def disconnect(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
        self.is_connected = False