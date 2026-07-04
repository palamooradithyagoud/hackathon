"""
Structured logging system.
Provides a configured logger and JSONL file writers for audit trails.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.config import settings


def get_logger(name: str = "faculty_rag") -> logging.Logger:
    """Return a configured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def append_jsonl(filepath: Path, data: dict) -> None:
    """Append a JSON object as a line to a JSONL file."""
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    try:
        # Ensure the directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.error(f"Failed to append to log file {filepath}: {e}. Standard log payload: {data}")


def log_decision(decision: dict) -> None:
    """Log a decision to the decisions audit trail."""
    append_jsonl(settings.LOGS_DIR / "decisions.jsonl", decision)


def log_feedback(feedback: dict) -> None:
    """Log user feedback to the feedback file."""
    append_jsonl(settings.LOGS_DIR / "feedback.jsonl", feedback)


logger = get_logger()
