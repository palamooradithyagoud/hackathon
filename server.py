"""
FastAPI Server.
Initializes database and coordinates middleware and router configuration.
"""

# Workaround for Vercel/AWS Lambda SQLite version compatibility with ChromaDB
import os
import sys
if os.getenv("VERCEL"):
    try:
        __import__('pysqlite3')
        sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    except ImportError:
        pass

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import router
from routers.semantic_router import semantic_router
from db.init_db import init_database
from core.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    try:
        init_database()
    except Exception as e:
        logger.error(f"Database initialization failed during startup: {e}")
        # In a local development environment, raise the error so the developer is aware.
        # On Vercel, catch it so the server can still run and serve static content.
        if not os.getenv("VERCEL"):
            raise
    yield
    # Shutdown sequence (no-op)
    pass

app = FastAPI(
    title="Faculty Research RAG & Collaboration API",
    description="Backend API for RAG, matchmaking, collaborations, and project recommendations.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(router, prefix="/api")
app.include_router(semantic_router, prefix="/api/semantic", tags=["Semantic Scholar"])

# Serve static assets
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve HTML templates directly
TEMPLATES_DIR = "templates"

@app.get("/")
@app.get("/index.html")
async def read_index():
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

@app.get("/dashboard.html")
async def read_dashboard():
    return FileResponse(os.path.join(TEMPLATES_DIR, "dashboard.html"))

@app.get("/chat.html")
async def read_chat():
    return FileResponse(os.path.join(TEMPLATES_DIR, "chat.html"))

@app.get("/paper_chat.html")
async def read_paper_chat():
    return FileResponse(os.path.join(TEMPLATES_DIR, "paper_chat.html"))

@app.get("/faculty.html")
async def read_faculty():
    return FileResponse(os.path.join(TEMPLATES_DIR, "faculty.html"))

@app.get("/faculty_chat.html")
async def read_faculty_chat():
    return FileResponse(os.path.join(TEMPLATES_DIR, "faculty_chat.html"))

@app.get("/research_gap.html")
async def read_research_gap():
    return FileResponse(os.path.join(TEMPLATES_DIR, "research_gap.html"))

@app.get("/collaboration.html")
async def read_collaboration():
    return FileResponse(os.path.join(TEMPLATES_DIR, "collaboration.html"))

@app.get("/citation_graph.html")
async def read_citation_graph():
    return FileResponse(os.path.join(TEMPLATES_DIR, "citation_graph.html"))

@app.get("/analytics.html")
async def read_analytics():
    return FileResponse(os.path.join(TEMPLATES_DIR, "analytics.html"))

@app.get("/profile.html")
async def read_profile():
    return FileResponse(os.path.join(TEMPLATES_DIR, "profile.html"))

@app.get("/{catchall:path}")
async def read_catchall(catchall: str):
    # Fallback to 404
    path_404 = os.path.join(TEMPLATES_DIR, "404.html")
    if os.path.exists(path_404):
        return FileResponse(path_404, status_code=404)
    return {"error": "Page not found"}

# Export app for Vercel handler
handler = app

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
