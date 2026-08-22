"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import documents, matching, stats

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TriMatch API",
    description="AI-powered three-way match for accounts payable",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(matching.router, prefix="/api/match", tags=["matching"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "trimatch"}