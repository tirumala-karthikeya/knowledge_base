from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db
from app.routers import documents, search

# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Base & Document Management System",
    description="A system for uploading, storing, searching, and managing documents with version tracking",
    version="1.0.0"
)

# CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized")

# Include routers
app.include_router(documents.router)
app.include_router(search.router)


@app.get("/")
def root():
    """
    Root endpoint - API information.
    """
    return {
        "message": "Knowledge Base & Document Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /documents/upload",
            "list": "GET /documents",
            "search": "GET /documents/search",
            "versions": "GET /documents/{document_id}/versions",
            "download": "GET /documents/{document_id}/download"
        }
    }

