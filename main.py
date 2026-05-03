from fastapi import FastAPI
from app.api.routers import qdrant_router, index_router, status_router, rag_router
from app.core.generation_config import generation_config


app = FastAPI(
    title="RAG System API",
    description="RAG система для генерации ответов",
    version="2.0.0",
    docs_url="/docs"
)


@app.get("/")
async def root():
    return {
        "service": "RAG System",
        "status": "running",
        "mode": generation_config.MODE
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "mode": generation_config.MODE}


app.include_router(qdrant_router.router, prefix="/api/v1/qdrant", tags=["Qdrant"])
app.include_router(index_router.router, prefix="/api/v1/index", tags=["Index"])
app.include_router(status_router.router, prefix="/api/v1/status", tags=["Status"])
app.include_router(rag_router.router, prefix="/api/v1/rag", tags=["RAG"])