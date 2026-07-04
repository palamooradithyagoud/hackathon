"""
Configuration module for Semantic Scholar integration.
"""

import os
from core.config import settings

SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "s2k-gzCmX6DhAdJs4t96ibY8a5ti7Y8E6o6pq84rVU20").strip()
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_CACHE_TTL_HOURS = 24
