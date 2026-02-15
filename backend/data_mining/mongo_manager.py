import json
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import json_util

from .base import BaseDataManager
from ..utils.responses import create_response


class MongoManager(BaseDataManager):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.uri = self.config.get("URI") or self.config.get("uri")
        self.host = self.config.get("HOST") or self.config.get("host")
        self.port = int(self.config.get("PORT") or self.config.get("port", 27017))
        self.user = self.config.get("USER") or self.config.get("user")

        pwd = self.config.get("PASSWORD") or self.config.get("password")
        self.password = (
            pwd.get_secret_value() if hasattr(pwd, "get_secret_value") else pwd
        )

        self.database_name = self.config.get("DATABASE") or self.config.get("database")
        self.timeout = int(self.config.get("SERVER_SELECTION_TIMEOUT_MS", 5000))

        self.client: Optional[MongoClient] = None
        self.db = None

    def connect(self) -> bool:
        if self.client:
            return True

        try:
            if self.uri:
                self.client = MongoClient(
                    self.uri, serverSelectionTimeoutMS=self.timeout
                )
            else:
                auth_part = ""
                if self.user and self.password:
                    auth_part = f"{self.user}:{self.password}@"

                host_str = self.host or "localhost"
                connection_str = f"mongodb://{auth_part}{host_str}:{self.port}/"
                self.client = MongoClient(
                    connection_str, serverSelectionTimeoutMS=self.timeout
                )

            self.client.admin.command("ping")
            self.db = self.client[self.database_name]
            self.is_connected = True
            return True

        except ConnectionFailure as c:
            self.is_connected = False
            return False
        except Exception:
            self.is_connected = False
            return False

    def test_connection(self) -> Any:
        try:
            if not self.connect():
                return create_response(
                    success=False, message="Failed to reach MongoDB server"
                )

            server_info = self.client.server_info()
            return create_response(
                success=True,
                message=f"Connected to MongoDB version {server_info.get('version')}",
                data={"version": server_info.get("version")},
            )
        except Exception as e:
            return create_response(
                success=False, message="Connection Error", error=str(e)
            )

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
                        if key == "_id":
                            col_type = "ObjectId"
                        else:
                            col_type = type(value).__name__

                        columns.append(f"{key}: {col_type}")

                row_count = self.db[col_name].estimated_document_count()

                schema_map[col_name] = {"row_count": row_count, "columns": columns}

            return create_response(
                success=True,
                data={"total_tables": len(collections), "tables": schema_map},
            )

        except Exception as e:
            return create_response(
                success=False, message="MongoDB Schema Extraction Failed", error=str(e)
            )

    def execute_query(self, query: str) -> Any:
        if not self.connect():
            return create_response(success=False, message="Database disconnected")

        try:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                return create_response(
                    success=False,
                    message="Invalid JSON format. Mongo queries must be JSON.",
                )

            target_collection = query_dict.get("collection")
            if not target_collection:
                return create_response(
                    success=False, message="Missing 'collection' key in query JSON."
                )

            operation = query_dict.get("operation", "find")
            db_filter = query_dict.get("filter", {})

            if operation == "count":
                count = self.db[target_collection].count_documents(db_filter)
                return create_response(
                    success=True,
                    data={
                        "columns": ["total"],
                        "rows": [{"total": count}],
                        "row_count": 1,
                    },
                )

            limit = int(query_dict.get("limit", 100))
            cursor = self.db[target_collection].find(db_filter, {"_id": 0}).limit(limit)

            rows = json.loads(json_util.dumps(list(cursor)))
            columns = list(rows[0].keys()) if rows else []

            return create_response(
                success=True,
                data={"columns": columns, "rows": rows, "row_count": len(rows)},
            )

        except Exception as e:
            return create_response(
                success=False, message="Query Execution Failed", error=str(e)
            )

    def disconnect(self):
        if self.client:
            self.client.close()
        self.is_connected = False
