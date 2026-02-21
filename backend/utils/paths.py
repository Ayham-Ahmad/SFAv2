from pathlib import Path

current_file_path = Path(__file__).resolve()

BASE_DIR = current_file_path.parents[2]

RAG_BASE_DIR = BASE_DIR / "backend" / "core" / "RAG"
RAG_DATA_DIR = RAG_BASE_DIR / "Data"
RAG_VECTOR_DB_DIR = RAG_BASE_DIR / "VectorDB"