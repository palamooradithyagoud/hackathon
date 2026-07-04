"""
semantic_router.py — Flask router for Semantic Scholar services.
Defines endpoints for paper details, search, related recommendations, and trends.
"""

from typing import List, Optional
from flask import Blueprint, request, jsonify
from pydantic import BaseModel, ValidationError
from services.semantic_scholar_service import SemanticScholarService
from rag.retriever import ChromaRetriever
from core.logger import logger

semantic_blueprint = Blueprint("semantic", __name__)
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

@semantic_blueprint.route("/search", methods=["GET"])
async def search_endpoint():
    """Search papers on Semantic Scholar."""
    query = request.args.get("query")
    if not query:
        return jsonify({"detail": "Missing query parameter"}), 400
    limit = request.args.get("limit", default=10, type=int)
    
    try:
        results = await s2_service.search_papers(query, limit)
        validated = [PaperResponse.model_validate(p).model_dump() for p in results]
        return jsonify(validated)
    except Exception as e:
        logger.error(f"[S2 Router] Search error: {e}")
        return jsonify({"detail": str(e)}), 500

@semantic_blueprint.route("/paper/<paper_id>", methods=["GET"])
async def paper_details_endpoint(paper_id: str):
    """Retrieve full details of a paper by ID."""
    try:
        details = await s2_service.get_paper_details(paper_id)
        if not details:
            return jsonify({"detail": "Paper not found on Semantic Scholar"}), 404
        validated = PaperResponse.model_validate(details).model_dump()
        return jsonify(validated)
    except Exception as e:
        logger.error(f"[S2 Router] Paper details error: {e}")
        return jsonify({"detail": str(e)}), 500

@semantic_blueprint.route("/author/<author_id>", methods=["GET"])
async def author_details_endpoint(author_id: str):
    """Retrieve author information and publications."""
    try:
        details = await s2_service.get_author_details(author_id)
        if not details:
            return jsonify({"detail": "Author not found on Semantic Scholar"}), 404
        validated = AuthorResponse.model_validate(details).model_dump()
        return jsonify(validated)
    except Exception as e:
        logger.error(f"[S2 Router] Author details error: {e}")
        return jsonify({"detail": str(e)}), 500

@semantic_blueprint.route("/related", methods=["GET"])
async def related_endpoint():
    """Find related papers for a given paper ID."""
    paper_id = request.args.get("paper_id")
    if not paper_id:
        return jsonify({"detail": "Missing paper_id parameter"}), 400
    limit = request.args.get("limit", default=5, type=int)
    
    try:
        results = await s2_service.get_related_papers(paper_id, limit)
        validated = [RelatedResponse.model_validate(p).model_dump() for p in results]
        return jsonify(validated)
    except Exception as e:
        logger.error(f"[S2 Router] Related papers error: {e}")
        return jsonify({"detail": str(e)}), 500

@semantic_blueprint.route("/graph/<paper_id>", methods=["GET"])
async def citation_graph_endpoint(paper_id: str):
    """Retrieve citation relationship data formatted for NetworkX / PyVis."""
    try:
        graph_data = await s2_service.generate_citation_graph(paper_id)
        validated = CitationGraphResponse.model_validate(graph_data).model_dump()
        return jsonify(validated)
    except Exception as e:
        logger.error(f"[S2 Router] Graph generation error: {e}")
        return jsonify({"detail": str(e)}), 500

@semantic_blueprint.route("/trends", methods=["GET"])
async def trends_endpoint():
    """Hybrid trend search combining local ChromaDB context and Semantic Scholar search."""
    query = request.args.get("query")
    if not query:
        return jsonify({"detail": "Missing query parameter"}), 400
    limit = request.args.get("limit", default=5, type=int)
    
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

        resp = {
            "local_papers": local_papers,
            "external_papers": external_results
        }
        validated = HybridSearchResponse.model_validate(resp).model_dump()
        return jsonify(validated)
    except Exception as e:
        logger.error(f"[S2 Router] Trends error: {e}")
        return jsonify({"detail": str(e)}), 500

@semantic_blueprint.route("/recommend", methods=["GET"])
async def recommend_endpoint():
    """Recommend papers classified into highly cited, similar, and latest categories."""
    query = request.args.get("query")
    if not query:
        return jsonify({"detail": "Missing query parameter"}), 400
        
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

        resp = {
            "highly_cited": highly_cited,
            "similar": similar,
            "latest": latest
        }
        validated = RecommendResponse.model_validate(resp).model_dump()
        return jsonify(validated)
    except Exception as e:
        logger.error(f"[S2 Router] Recommend error: {e}")
        return jsonify({"detail": str(e)}), 500
