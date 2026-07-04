"""
semantic_router.py — FastAPI router for Semantic Scholar services.
Defines endpoints for paper details, search, related recommendations, and trends.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from services.semantic_scholar_service import SemanticScholarService
from rag.retriever import ChromaRetriever
from core.logger import logger

router = APIRouter()
s2_service = SemanticScholarService()
retriever = ChromaRetriever()

# --- Schemas ---

class PaperResponse(BaseModel):
    paperId: Optional[str]
    title: Optional[str]
    abstract: Optional[str]
    authors: List[str]
    year: Optional[int]
    venue: Optional[str]
    doi: Optional[str]
    url: Optional[str]
    citation_count: int
    influential_citation_count: int
    fields_of_study: List[str]
    tldr: Optional[str]

class RelatedResponse(BaseModel):
    paperId: Optional[str]
    title: Optional[str]
    authors: List[str]
    year: Optional[int]
    venue: Optional[str]
    citation_count: int
    influential_citation_count: int

class AuthorResponse(BaseModel):
    authorId: Optional[str]
    name: Optional[str]
    affiliations: List[str]
    homepage: Optional[str]
    h_index: Optional[int]
    publication_count: int
    citation_count: int
    papers: List[dict]

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    color: str

class GraphLink(BaseModel):
    source: str
    target: str

class CitationGraphResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]

class HybridSearchResponse(BaseModel):
    local_papers: List[dict]
    external_papers: List[dict]

class RecommendResponse(BaseModel):
    highly_cited: List[dict]
    similar: List[dict]
    latest: List[dict]

# --- Endpoints ---

@router.get("/search", response_model=List[PaperResponse])
async def search_endpoint(
    query: str = Query(..., description="The query string to search papers"),
    limit: int = Query(10, description="Max results limit")
):
    """Search papers on Semantic Scholar."""
    try:
        return await s2_service.search_papers(query, limit)
    except Exception as e:
        logger.error(f"[S2 Router] Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/paper/{paper_id}", response_model=PaperResponse)
async def paper_details_endpoint(paper_id: str):
    """Retrieve full details of a paper by ID."""
    try:
        details = await s2_service.get_paper_details(paper_id)
        if not details:
            raise HTTPException(status_code=404, detail="Paper not found on Semantic Scholar")
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[S2 Router] Paper details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/author/{author_id}", response_model=AuthorResponse)
async def author_details_endpoint(author_id: str):
    """Retrieve author information and publications."""
    try:
        details = await s2_service.get_author_details(author_id)
        if not details:
            raise HTTPException(status_code=404, detail="Author not found on Semantic Scholar")
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[S2 Router] Author details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/related", response_model=List[RelatedResponse])
async def related_endpoint(
    paper_id: str = Query(..., description="The Semantic Scholar paper ID"),
    limit: int = Query(5, description="Max recommendations limit")
):
    """Find related papers for a given paper ID."""
    try:
        return await s2_service.get_related_papers(paper_id, limit)
    except Exception as e:
        logger.error(f"[S2 Router] Related papers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph/{paper_id}", response_model=CitationGraphResponse)
async def citation_graph_endpoint(paper_id: str):
    """Retrieve citation relationship data formatted for NetworkX / PyVis."""
    try:
        return await s2_service.generate_citation_graph(paper_id)
    except Exception as e:
        logger.error(f"[S2 Router] Graph generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends", response_model=HybridSearchResponse)
async def trends_endpoint(
    query: str = Query(..., description="Trend topic search query"),
    limit: int = Query(5, description="Limit for both local and external papers")
):
    """Hybrid trend search combining local ChromaDB context and Semantic Scholar search."""
    try:
        # Get external results
        external_results = await s2_service.search_papers(query, limit=limit)

        # Get local results
        local_chunks = retriever.retrieve(query, n_results=limit)
        
        # Format local papers to avoid duplicate files in lists
        local_papers = []
        seen_files = set()
        for chunk in local_chunks:
            source_file = chunk["metadata"].get("source", "unknown")
            if source_file not in seen_files:
                seen_files.add(source_file)
                # Attempt to enrich with citations in background
                enriched = await s2_service.enrich_paper(source_file)
                local_papers.append({
                    "title": source_file,
                    "snippet": chunk["document"][:200] + "...",
                    "distance": chunk["distance"],
                    "citation_count": enriched.get("citation_count", 0) if enriched else 0,
                    "influential_citation_count": enriched.get("influential_citation_count", 0) if enriched else 0,
                    "doi": enriched.get("doi") if enriched else None,
                    "venue": enriched.get("venue") if enriched else None
                })

        return {
            "local_papers": local_papers,
            "external_papers": external_results
        }
    except Exception as e:
        logger.error(f"[S2 Router] Trends error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommend", response_model=RecommendResponse)
async def recommend_endpoint(query: str = Query(..., description="Topic of interest")):
    """Recommend papers classified into highly cited, similar, and latest categories."""
    try:
        # Search for general papers
        papers = await s2_service.search_papers(query, limit=15)
        
        # Classify papers
        highly_cited = sorted(papers, key=lambda x: x.get("citation_count", 0), reverse=True)[:5]
        similar = papers[:5]  # relevance based on search rank
        
        # Sort by year to get latest
        latest = sorted(
            [p for p in papers if p.get("year") is not None], 
            key=lambda x: x.get("year", 0), 
            reverse=True
        )[:5]

        return {
            "highly_cited": highly_cited,
            "similar": similar,
            "latest": latest
        }
    except Exception as e:
        logger.error(f"[S2 Router] Recommend error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
