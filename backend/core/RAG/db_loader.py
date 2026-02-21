import os
import sentry_sdk
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def load_vector_db():
    try:
        print("Loading HuggingFace Embeddings (all-MiniLM-L6-v2)...")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        DB_PATH = os.path.join(os.getcwd(), "backend", "core", "RAG", "VectorDB")
        
        print(f"Loading ChromaDB from {DB_PATH}...")
        vector_db = Chroma(
            persist_directory=DB_PATH,
            embedding_function=embeddings
        )
        
        print("✅ Vector DB loaded successfully.")
        return vector_db
        
    except Exception as e:
        print(f"❌ Error loading Vector DB: {e}")
        sentry_sdk.capture_exception(e)
        return None