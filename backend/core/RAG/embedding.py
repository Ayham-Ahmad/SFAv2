import os
from typing import List
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import sentry_sdk

from api.config import settings

class FinancialRAGEmbedder:
    def __init__(self, data_path: str, persist_directory: str):
        self.data_path = data_path
        self.persist_directory = persist_directory

        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", " "]
        )

    def extract_text_from_pdf(self, file_path: str) -> str:
        try:
            reader = PdfReader(file_path)
            text = ""

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text

            return text.strip()

        except Exception as e:
            sentry_sdk.capture_exception(e)
            print(f"❌ Error reading {file_path}: {e}")
            return ""

    def get_category(self, filename: str) -> str:
        fn_upper = filename.upper()
        if fn_upper.startswith("MACRO_"):
            return "macro"
        elif fn_upper.startswith("STRATEGY_"):
            return "strategy"
        elif fn_upper.startswith("COMPLIANCE_"):
            return "compliance"
        return "general"

    def run(self):
        documents: List[Document] = []

        print(f"📂 Processing files in: {self.data_path}")

        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Data path not found: {self.data_path}")

        for filename in os.listdir(self.data_path):
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(self.data_path, filename)
                category = self.get_category(filename)

                print(f"📄 Extracting: {filename} [{category}]")
                raw_text = self.extract_text_from_pdf(file_path)

                if not raw_text:
                    continue

                chunks = self.text_splitter.split_text(raw_text)

                for i, chunk in enumerate(chunks):
                    documents.append(
                        Document(
                            page_content=chunk,
                            metadata={
                                "source": filename,
                                "category": category,
                                "chunk_id": i
                            }
                        )
                    )

        if not documents:
            print("❌ No documents found to process.")
            return

        print(f"🚀 Embedding {len(documents)} chunks into ChromaDB...")

        vector_db = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )

        print("✅ Embedding Complete! Vector DB saved.")


if __name__ == "__main__":
    if hasattr(settings, 'SENTRY_DSN'):
        sentry_sdk.init(dsn=settings.SENTRY_DSN)
        
    DATA_PATH = r"C:\Users\Ayham\Desktop\iFYP\Codes\SFA_adv\backend\core\RAG\Data"
    DB_PATH = r"C:\Users\Ayham\Desktop\iFYP\Codes\SFA_adv\backend\core\RAG\VectorDB"

    embedder = FinancialRAGEmbedder(DATA_PATH, DB_PATH)
    embedder.run()