import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sentry_sdk
from .config import settings 

from api.routes.auth        import router as auth_router
from api.routes.tents       import router as tents_router
from api.routes.users       import router as users_router
from api.routes.admin       import router as admin_router
from api.routes.super_admin import router as super_admin_router
from api.routes.chat        import router as chat_router
from api.routes.graphs      import router as graphs_router
from api.routes.pages       import router as pages_router

from .database.database import engine, Base

# Warmup
@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.utils.encryption import validate_encryption_key
    validate_encryption_key()
    print("[OK] Encryption key valid.")
    
    print("Connecting to Database...")
    Base.metadata.create_all(bind=engine)

    print("Warming up AI modules and Vector DB...")
    from langchain_groq import ChatGroq
    from backend.core.RAG.db_loader import load_vector_db 
    vector_db = load_vector_db()
    if vector_db:
        app.state.vector_db = vector_db
        print("[OK] Vector DB attached to app.state.")

    print("Warmup complete")
    yield

    print("Disposing Database Engine...")
    engine.dispose()
    
    if hasattr(app.state, "vector_db"):
        del app.state.vector_db
        print("Cleared Vector DB from memory.")
        
    print("Shutdown complete.")

sentry_sdk.init(dsn=settings.SENTRY_SDK_DNS, send_default_pii=True)

app = FastAPI(title="SFA", version="3.11", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tents_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(super_admin_router)
app.include_router(chat_router)
app.include_router(graphs_router)
app.include_router(pages_router)

app.mount("/static", StaticFiles(directory="./frontend/static"), name="static")

if __name__ == "__main__":
    print("Starting SFA Server...")
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)