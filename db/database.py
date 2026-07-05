"""
SQLAlchemy Database Connection.
Sets up engine and sessionmaker for SQLite or PostgreSQL storage.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import settings
import os

# Create engine for primary database (can be Supabase/PostgreSQL or local SQLite fallback)
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a local-only SQLite engine for caching and metadata to ensure it never touches Supabase
if os.getenv("VERCEL"):
    cache_db_path = "/tmp/local_cache.db"
else:
    cache_db_path = os.path.join(settings.PROJECT_ROOT, "local_cache.db")
cache_engine = create_engine(f"sqlite:///{cache_db_path}", connect_args={"check_same_thread": False})
CacheSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cache_engine)

Base = declarative_base()

def get_db():
    """Dependency generator for main database sessions (Supabase / local DB)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_cache_db():
    """Dependency generator for cache-only database sessions (local SQLite)."""
    db = CacheSessionLocal()
    try:
        yield db
    finally:
        db.close()
