from typing import List, Dict, Any, Optional
from langchain_chroma import Chroma

from .base_tool import BaseTool


class AdvisoryRAGTool(BaseTool):
    """
    Retrieves institutional financial knowledge from the vector database (RAG).
    
    Input format from LLM:
        [{"query": "What are key liquidity ratios?", "category": "compliance"}, ...]
    """
    name = "advisory"
    description = "Provides expert financial advice based on retrieved data and a user question. Input: a list of {\"query\": \"concept-level search query\", \"category\": \"macro|compliance|strategy\"}. You MUST extract the core financial CONCEPT for the query (do NOT copy the user's raw question). Valid categories: 'macro' (economic outlook, GDP, inflation, market trends), 'compliance' (regulations, IPS, GAAP/IFRS standards), 'strategy' (financial ratios, modeling, trading patterns, portfolio management). Output: top-3 structured advisory response."
    input_type = list
    requires_retrieval = False
    input_format = '[{"query": "economic outlook GDP growth inflation forecast 2026", "category": "macro"}]'

    def __init__(self, vector_db: Chroma = None):
        self.vector_db = vector_db

    def execute(self, input_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        # Get vector_db from context if not already set
        if not self.vector_db:
            request = context.get("request")
            if request:
                self.vector_db = getattr(request.app.state, "vector_db", None)

        if not self.vector_db:
            return {"success": False, "error": "Knowledge Base not initialized."}

        result = self.get_institutional_knowledge(input_data)
        return {"success": True, "data": result}


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