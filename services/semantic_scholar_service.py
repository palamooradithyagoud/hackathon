"""
Semantic Scholar API Integration Service.
Provides paper search, detail lookup, author details, recommendations,
caching, retries with backoff, metadata enrichment, and hybrid search.
"""

import time
import httpx
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from config.semantic_config import SEMANTIC_SCHOLAR_API_KEY, SEMANTIC_SCHOLAR_BASE_URL
from utils.semantic_cache import SemanticCacheManager
from db.database import get_db
from db.models import PaperEnrichment
from core.logger import logger

class SemanticScholarService:
    """Production-grade service wrapper for the Semantic Scholar API."""

    def __init__(self):
        self.headers = {}
        if SEMANTIC_SCHOLAR_API_KEY:
            self.headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
        self.client = httpx.AsyncClient(timeout=10.0, headers=self.headers)

    async def _request_with_backoff(self, url: str, params: dict | None = None) -> dict | None:
        """
        Execute API request with exponential backoff for rate limits (429) or timeouts.
        """
        # Create cache key
        cache_key = f"{url}_{sorted(params.items()) if params else ''}"
        cached = SemanticCacheManager.get(cache_key)
        if cached is not None:
            return cached

        backoff = 0.5
        max_retries = 4
        start_time = time.perf_counter()

        for attempt in range(max_retries):
            try:
                logger.info(f"[S2 Service] Requesting: {url} (Attempt {attempt+1})")
                response = await self.client.get(url, params=params)
                latency = time.perf_counter() - start_time
                logger.debug(f"[S2 Service] Response latency: {latency:.3f}s")

                if response.status_code == 200:
                    data = response.json()
                    SemanticCacheManager.set(cache_key, data)
                    return data
                elif response.status_code == 429:
                    logger.warning(f"[S2 Service] Rate limit 429 hit. Backing off for {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(f"[S2 Service] Request failed with HTTP {response.status_code}: {response.text}")
                    return None
            except Exception as e:
                logger.error(f"[S2 Service] Network/parsing error: {e}")
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(backoff)
                backoff *= 2

        return None

    async def search_papers(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search papers by topic, title, keyword or author.
        """
        url = f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/search"
        fields = "title,abstract,authors,year,venue,externalIds,url,citationCount,influentialCitationCount,fieldsOfStudy,tldr"
        params = {"query": query, "limit": limit, "fields": fields}
        
        res = await self._request_with_backoff(url, params)
        if not res or "data" not in res:
            return []

        papers = []
        for p in res.get("data", []):
            papers.append({
                "paperId": p.get("paperId"),
                "title": p.get("title"),
                "abstract": p.get("abstract"),
                "authors": [a.get("name") for a in p.get("authors", [])],
                "year": p.get("year"),
                "venue": p.get("venue"),
                "doi": p.get("externalIds", {}).get("DOI"),
                "url": p.get("url"),
                "citation_count": p.get("citationCount", 0),
                "influential_citation_count": p.get("influentialCitationCount", 0),
                "fields_of_study": p.get("fieldsOfStudy", []),
                "tldr": p.get("tldr", {}).get("text") if p.get("tldr") else None
            })
        return papers

    async def get_paper_details(self, paper_id: str) -> dict | None:
        """
        Get details for a paper by ID (including citations, references, and external IDs).
        """
        url = f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/{paper_id}"
        fields = "paperId,title,abstract,authors,year,venue,externalIds,url,citationCount,influentialCitationCount,fieldsOfStudy,tldr,references,citations"
        params = {"fields": fields}

        p = await self._request_with_backoff(url, params)
        if not p:
            return None

        return {
            "paperId": p.get("paperId"),
            "title": p.get("title"),
            "abstract": p.get("abstract"),
            "authors": [a.get("name") for a in p.get("authors", [])],
            "year": p.get("year"),
            "venue": p.get("venue"),
            "doi": p.get("externalIds", {}).get("DOI"),
            "url": p.get("url"),
            "citation_count": p.get("citationCount", 0),
            "influential_citation_count": p.get("influentialCitationCount", 0),
            "fields_of_study": p.get("fieldsOfStudy", []),
            "tldr": p.get("tldr", {}).get("text") if p.get("tldr") else None,
            "references": [{"paperId": ref.get("paperId"), "title": ref.get("title")} for ref in p.get("references", [])],
            "citations": [{"paperId": cit.get("paperId"), "title": cit.get("title")} for cit in p.get("citations", [])]
        }

    async def get_author_details(self, author_id: str) -> dict | None:
        """
        Get details for an author.
        """
        url = f"{SEMANTIC_SCHOLAR_BASE_URL}/author/{author_id}"
        fields = "authorId,name,affiliations,homepage,hIndex,paperCount,citationCount,papers"
        params = {"fields": fields}

        a = await self._request_with_backoff(url, params)
        if not a:
            return None

        return {
            "authorId": a.get("authorId"),
            "name": a.get("name"),
            "affiliations": a.get("affiliations", []),
            "homepage": a.get("homepage"),
            "h_index": a.get("hIndex"),
            "publication_count": a.get("paperCount", 0),
            "citation_count": a.get("citationCount", 0),
            "papers": [{"paperId": p.get("paperId"), "title": p.get("title"), "year": p.get("year")} for p in a.get("papers", [])]
        }

    async def get_related_papers(self, paper_id: str, limit: int = 5) -> list[dict]:
        """
        Get related papers ranked by relevance from Semantic Scholar Recommendations endpoint.
        """
        url = f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{paper_id}"
        fields = "title,abstract,authors,year,venue,citationCount,influentialCitationCount"
        params = {"limit": limit, "fields": fields}

        res = await self._request_with_backoff(url, params)
        if not res or "recommendedPapers" not in res:
            # Fallback to search query based on title
            details = await self.get_paper_details(paper_id)
            if details and details.get("title"):
                return await self.search_papers(details["title"], limit=limit)
            return []

        papers = []
        for p in res.get("recommendedPapers", []):
            papers.append({
                "paperId": p.get("paperId"),
                "title": p.get("title"),
                "authors": [a.get("name") for a in p.get("authors", [])],
                "year": p.get("year"),
                "venue": p.get("venue"),
                "citation_count": p.get("citationCount", 0),
                "influential_citation_count": p.get("influentialCitationCount", 0)
            })
        return papers

    async def generate_citation_graph(self, paper_id: str) -> dict:
        """
        Returns nodes and links representation of references/citations for NetworkX/PyVis.
        """
        details = await self.get_paper_details(paper_id)
        if not details:
            return {"nodes": [], "links": []}

        nodes = [{"id": paper_id, "label": details["title"][:30] + "...", "type": "root", "color": "#4F46E5"}]
        links = []

        # Add references (nodes cited by root)
        for ref in details["references"][:10]:
            ref_id = ref["paperId"]
            if ref_id:
                nodes.append({"id": ref_id, "label": ref["title"][:25] + "...", "type": "reference", "color": "#06B6D4"})
                links.append({"source": paper_id, "target": ref_id})

        # Add citations (nodes citing root)
        for cit in details["citations"][:10]:
            cit_id = cit["paperId"]
            if cit_id:
                nodes.append({"id": cit_id, "label": cit["title"][:25] + "...", "type": "citation", "color": "#10B981"})
                links.append({"source": cit_id, "target": paper_id})

        return {"nodes": nodes, "links": links}

    async def enrich_paper(self, title: str) -> dict | None:
        """
        Enriches a local paper with Semantic Scholar metadata, saving results in SQLite.
        """
        db: Session = next(get_db())
        try:
            # Normalize title key to lower, alphanumeric only
            title_key = "".join(e for e in title.lower() if e.isalnum())
            if not title_key:
                return None

            # Check if enrichment already exists in SQLite
            cached = db.query(PaperEnrichment).filter(PaperEnrichment.paper_title_key == title_key).first()
            if cached:
                # If cached and younger than 7 days, return it
                age = datetime.now(timezone.utc) - cached.updated_at.replace(tzinfo=timezone.utc)
                if age.days < 7:
                    logger.debug(f"[S2 Enrich] Found existing sqlite record for: {title}")
                    return {
                        "s2_paper_id": cached.s2_paper_id,
                        "doi": cached.doi,
                        "venue": cached.venue,
                        "year": cached.year,
                        "citation_count": cached.citation_count,
                        "influential_citation_count": cached.influential_citation_count,
                        "authors": cached.authors.split(",") if cached.authors else [],
                        "fields_of_study": cached.fields_of_study.split(",") if cached.fields_of_study else []
                    }

            # Search Semantic Scholar by title
            results = await self.search_papers(title, limit=1)
            if not results:
                logger.debug(f"[S2 Enrich] No online match found for: {title}")
                return None

            s2_paper = results[0]
            authors_str = ",".join(s2_paper["authors"]) if s2_paper["authors"] else ""
            fields_str = ",".join(s2_paper["fields_of_study"]) if s2_paper["fields_of_study"] else ""

            if cached:
                cached.s2_paper_id = s2_paper["paperId"]
                cached.doi = s2_paper["doi"]
                cached.venue = s2_paper["venue"]
                cached.year = s2_paper["year"]
                cached.citation_count = s2_paper["citation_count"]
                cached.influential_citation_count = s2_paper["influential_citation_count"]
                cached.authors = authors_str
                cached.fields_of_study = fields_str
                cached.updated_at = datetime.now(timezone.utc)
            else:
                new_enrich = PaperEnrichment(
                    paper_title_key=title_key,
                    s2_paper_id=s2_paper["paperId"],
                    doi=s2_paper["doi"],
                    venue=s2_paper["venue"],
                    year=s2_paper["year"],
                    citation_count=s2_paper["citation_count"],
                    influential_citation_count=s2_paper["influential_citation_count"],
                    authors=authors_str,
                    fields_of_study=fields_str,
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(new_enrich)

            db.commit()
            logger.info(f"[S2 Enrich] Successfully enriched paper: {title}")
            return s2_paper

        except Exception as e:
            logger.error(f"[S2 Enrich] Error during enrichment: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    async def close(self):
        """Close client sessions."""
        await self.client.aclose()
