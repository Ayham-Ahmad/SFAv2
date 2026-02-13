import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sentry_sdk
from .config import settings 

from api.routes.auth import router as auth_router
from api.routes.tents import router as tents_router
from api.routes.users import router as me_router
from api.routes.admin import router as admin_router
from api.routes.super_admin import router as super_admin_router

from .database.database import engine, Base

# Warmup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to Database...")
    Base.metadata.create_all(bind=engine)

    print("Warming up AI modules...")
    from langchain_groq import ChatGroq
    print("Warmup complete")
    yield

    print("Disposing Database Engine...")
    engine.dispose()

sentry_sdk.init(
    dsn=settings.SENTRY_SDK_DNS,
    send_default_pii=True,
)

# Initialize the App
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
app.include_router(me_router)
app.include_router(admin_router)
app.include_router(super_admin_router)

app.mount("/static", StaticFiles(directory="./frontend/static"), name="static")


if __name__ == "__main__":
    print("Starting SFA Server...")
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)