import json
from typing import Any, Dict, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson import json_util

from .base import BaseDataManager
from ..utils.responses import create_response

class MongoManager(BaseDataManager):
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.uri = self.config.get("URI") or self.config.get("uri")
        
        self.host = self.config.get("HOST") or self.config.get("host", "localhost")
        self.port = int(self.config.get("PORT") or self.config.get("port", 27017))
        self.user = self.config.get("USER") or self.config.get("user")
        self.password = self.config.get("PASSWORD") or self.config.get("password")
        self.database_name = self.config.get("DATABASE") or self.config.get("database")
        
        self.client: Optional[MongoClient] = None
        self.db = None

    def connect(self) -> bool:
        if self.client:
            return True
            
        try:
            if self.uri:
                self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            else:
                auth_part = ""
                if self.user and self.password:
                    auth_part = f"{self.user}:{self.password}@"
                
                connection_str = f"mongodb://{auth_part}{self.host}:{self.port}/"
                self.client = MongoClient(connection_str, serverSelectionTimeoutMS=5000)
            
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            self.is_connected = True
            return True
            
        except (ConnectionFailure, OperationFailure):
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        try:
            if not self.connect():
                return create_response(success=False, message="Failed to reach MongoDB server")

            server_info = self.client.server_info()
            return create_response(
                success=True,
                message=f"Connected to MongoDB version {server_info.get('version')}",
                data={"version": server_info.get('version')}
            )
        except Exception as e:
            return create_response(success=False, message="Connection Error", error=str(e))

    def get_full_schema(self) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        try:
            collections = self.db.list_collection_names()
            schema_map = {}
            
            for col_name in collections:
                sample_doc = self.db[col_name].find_one()
                columns = []
                
                if sample_doc:
                    for key, value in sample_doc.items():
                        col_type = type(value).__name__
                        if key == "_id": 
                            col_type = "ObjectId"
                            
                        columns.append({
                            "name": key,
                            "type": col_type,
                            "nullable": True
                        })
                
                row_count = self.db[col_name].estimated_document_count()
                
                schema_map[col_name] = {
                    "columns": columns,
                    "row_count": row_count
                }

            return create_response(
                success=True,
                data={
                    "tables": collections,
                    "schema": schema_map,
                    "total_tables": len(collections)
                }
            )

        except Exception as e:
            return create_response(success=False, message="Schema Extraction Failed", error=str(e))

    def execute_query(self, query: str) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        try:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                return create_response(success=False, message="Invalid JSON format. Mongo queries must be JSON.")

            target_collection = query_dict.get("collection")
            if not target_collection:
                return create_response(success=False, message="Missing 'collection' key in query JSON.")

            db_filter = query_dict.get("filter", {}) 
            limit = int(query_dict.get("limit", 100))

            cursor = self.db[target_collection].find(db_filter).limit(limit)
            
            rows = json.loads(json_util.dumps(list(cursor)))
            
            columns = list(rows[0].keys()) if rows else []

            return create_response(
                success=True,
                data={
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows)
                }
            )

        except Exception as e:
            return create_response(success=False, message="Query Execution Failed", error=str(e))

    def disconnect(self):
        if self.client:
            self.client.close()
        self.is_connected = False