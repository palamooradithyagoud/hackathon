"""
Central configuration loader.
Reads all settings from .env and exposes them as typed attributes.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (override=True so changes to .env are always picked up)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # --- ChromaDB ---
        self.CHROMA_API_KEY: str = os.getenv("CHROMA_API_KEY", "")
        self.CHROMA_TENANT: str = os.getenv("CHROMA_TENANT", "")
        self.CHROMA_DATABASE: str = os.getenv("CHROMA_DATABASE", "")
        self.CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "pdf_documents")

        # --- Groq LLM ---
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        # Default to llama-4-scout; overridden by GROQ_MODEL in .env
        self.GROQ_MODEL: str = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

        # --- Tavily (optional) ---
        self.TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

        # --- Database ---
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL", f"sqlite:///{_PROJECT_ROOT / 'faculty_rag.db'}"
        )

        # --- Paths ---
        self.PROJECT_ROOT: Path = _PROJECT_ROOT
        self.LOGS_DIR: Path = _PROJECT_ROOT / "logs"
        self.LOGS_DIR.mkdir(exist_ok=True)

        # --- RAG tuning ---
        self.RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "8"))
        self.RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "1.2"))

        # --- SMTP Configuration ---
        self.SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER: str = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_FROM: str = os.getenv("SMTP_FROM", "")

        # --- Supabase Configuration ---
        self.SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://euuixlzgvwdgezjllemljw.supabase.co")
        self.SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
        self.SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

    @property
    def has_smtp(self) -> bool:
        return bool(self.SMTP_USER and self.SMTP_PASSWORD)

    @property
    def has_tavily(self) -> bool:
        return bool(self.TAVILY_API_KEY)

    @property
    def has_chroma(self) -> bool:
        return bool(self.CHROMA_API_KEY and self.CHROMA_TENANT and self.CHROMA_DATABASE)

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def has_supabase(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_ANON_KEY)


settings = Settings()

