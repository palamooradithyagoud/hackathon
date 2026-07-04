"""
Intelligent Caching module for Semantic Scholar API requests using SQLite backend.
Expirations default to 24 hours.
"""

import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import SemanticCache
from core.logger import logger

class SemanticCacheManager:
    """Manager for storing and retrieving caching requests in SQLite."""

    @staticmethod
    def get(cache_key: str) -> dict | list | None:
        """
        Retrieve a cached response if exists and not expired.
        """
        db: Session = next(get_db())
        try:
            now = datetime.now(timezone.utc)
            # Query db for cache key
            cached = db.query(SemanticCache).filter(SemanticCache.cache_key == cache_key).first()
            if not cached:
                logger.debug(f"[Semantic Cache] Miss for key: {cache_key}")
                return None

            # Handle datetime offset-naive vs offset-aware comparison
            expires_at = cached.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if now > expires_at:
                logger.debug(f"[Semantic Cache] Expired key: {cache_key}")
                # Clean up expired entry
                db.delete(cached)
                db.commit()
                return None

            logger.info(f"[Semantic Cache] Hit for key: {cache_key}")
            return json.loads(cached.response_json)
        except Exception as e:
            logger.error(f"[Semantic Cache] Error reading cache: {e}")
            return None
        finally:
            db.close()

    @staticmethod
    def set(cache_key: str, response_data: dict | list, ttl_hours: int = 24) -> None:
        """
        Save response data into SQLite cache.
        """
        db: Session = next(get_db())
        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(hours=ttl_hours)
            response_json = json.dumps(response_data)

            # Check if entry already exists to update
            cached = db.query(SemanticCache).filter(SemanticCache.cache_key == cache_key).first()
            if cached:
                cached.response_json = response_json
                cached.expires_at = expires_at
                cached.created_at = now
            else:
                new_cache = SemanticCache(
                    cache_key=cache_key,
                    response_json=response_json,
                    expires_at=expires_at,
                    created_at=now
                )
                db.add(new_cache)

            db.commit()
            logger.info(f"[Semantic Cache] Stored key: {cache_key} (expires in {ttl_hours}h)")
        except Exception as e:
            logger.error(f"[Semantic Cache] Error writing cache: {e}")
            db.rollback()
        finally:
            db.close()
