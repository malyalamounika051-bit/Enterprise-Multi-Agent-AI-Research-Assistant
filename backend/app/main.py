import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db.database import init_db
from .rag.vector_store import get_vector_store
from .observability.tracer import init_observability
from .api.endpoints import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print(f"[{settings.PROJECT_NAME}] Initializing database...")
    init_db()
    print(f"[{settings.PROJECT_NAME}] Initializing ChromaDB vector store...")
    vs = get_vector_store()
    print(f"[{settings.PROJECT_NAME}] Vector store loaded with {vs.collection.count()} chunks.")
    print(f"[{settings.PROJECT_NAME}] Initializing observability...")
    init_observability()
    yield
    # Shutdown actions
    print(f"[{settings.PROJECT_NAME}] Application shut down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Full-Stack Multi-Agent AI Research Assistant with LangSmith Observability and Isolated Memory",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "message": f"{settings.PROJECT_NAME} API is running.",
        "docs_url": "/docs",
        "api_prefix": settings.API_V1_PREFIX
    }
