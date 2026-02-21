from typing import List, Dict, Optional
from langchain_chroma import Chroma

class AdvisoryRAGTool:
    def __init__(self, vector_db: Chroma):
        self.vector_db = vector_db

    def get_institutional_knowledge(self, advisory_requests: Optional[List[Dict[str, str]]]) -> str:
        if not advisory_requests:
            return "No advisory research requested."

        compiled_knowledge = "--- START OF INSTITUTIONAL KNOWLEDGE BRIEF ---\n"

        for request in advisory_requests:
            query = request.get("query")
            category = request.get("category")
            
            search_filter = {"category": category.lower()} if category else None
            
            docs = self.vector_db.similarity_search(
                query, 
                k=3, 
                filter=search_filter
            )

            compiled_knowledge += f"\n### RESEARCH TASK: {query.upper()} (Layer: {category if category else 'General'})\n"
            
            if not docs:
                compiled_knowledge += "No specific matching documents found for this query.\n"
                continue

            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get("source", "Internal Resource")
                compiled_knowledge += f"Source [{i}]: {source}\n"
                compiled_knowledge += f"Content: {doc.page_content}\n"
                compiled_knowledge += "-" * 30 + "\n"

        compiled_knowledge += "\n--- END OF INSTITUTIONAL KNOWLEDGE BRIEF ---"
        return compiled_knowledge