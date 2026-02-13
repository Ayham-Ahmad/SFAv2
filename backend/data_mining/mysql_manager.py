import mysql.connector
from mysql.connector import Error
from typing import Dict, Any

from .base import BaseDataManager
from ..utils.responses import create_response

class MySQLManager(BaseDataManager):
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = self.config.get("HOST") or self.config.get("host")
        self.port = int(self.config.get("PORT") or self.config.get("port", 3306))
        self.user = self.config.get("USER") or self.config.get("user")
        self.password = self.config.get("PASSWORD") or self.config.get("password")
        self.database = self.config.get("DATABASE") or self.config.get("database")
        self.charset = self.config.get("CHARSET") or self.config.get("charset", "utf8mb4")
        self.conn = None

    def connect(self) -> bool:
        if self.conn and self.conn.is_connected():
            return True
        
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                connection_timeout=5
            )
            self.is_connected = self.conn.is_connected()
            return self.is_connected
        except Error:
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        try:
            if not self.connect():
                return create_response(success=False, message="Failed to reach MySQL server")

            if self.conn.is_connected():
                db_info = self.conn.get_server_info()
                return create_response(
                    success=True,
                    message=f"Connected to MySQL Server version {db_info}",
                    data={"version": db_info}
                )
        except Error as e:
            return create_response(success=False, message="MySQL Connection Error", error=str(e))

    def get_full_schema(self) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        try:
            query = """
                SELECT table_name, column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_schema = %s 
                ORDER BY table_name, ordinal_position;
            """
            
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(query, (self.database,))
            rows = cursor.fetchall()
            
            schema_map = {}
            tables_list = []
            
            for row in rows:
                t_name = row['table_name']
                if t_name not in schema_map:
                    schema_map[t_name] = {"columns": [], "row_count": 0}
                    tables_list.append(t_name)
                
                schema_map[t_name]["columns"].append({
                    "name": row['column_name'],
                    "type": row['data_type'],
                    "nullable": row['is_nullable'] == 'YES'
                })

            for t in tables_list:
                try:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM `{t}`")
                    count_res = cursor.fetchone()
                    schema_map[t]["row_count"] = count_res['cnt']
                except Error:
                    schema_map[t]["row_count"] = -1

            cursor.close()

            return create_response(
                success=True,
                data={
                    "tables": tables_list,
                    "schema": schema_map,
                    "total_tables": len(tables_list)
                }
            )

        except Error as e:
            return create_response(success=False, message="Schema Extraction Failed", error=str(e))

    def execute_query(self, query: str) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        clean_query = query.strip().upper()
        if not clean_query.startswith("SELECT") and not clean_query.startswith("SHOW"):
             return create_response(success=False, message="Security: Only READ operations allowed.")

        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(query)
            
            rows = cursor.fetchall()
            cursor.close()

            columns = list(rows[0].keys()) if rows else []

            return create_response(
                success=True,
                data={
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows)
                }
            )
        except Error as e:
            return create_response(success=False, message="Query Execution Failed", error=str(e))

    def disconnect(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()
        self.is_connected = False