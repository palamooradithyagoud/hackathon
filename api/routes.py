"""
FastAPI Routes.
Declares endpoints for chat, upload, collaboration, gap analysis, logs, and feedback.
"""

import os
import shutil
import tempfile
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from api.schemas import (
    ChatRequest, ChatResponse, 
    CollaborateRequest, CollaborateResponse,
    ProfessorModeRequest, ProfessorModeResponse,
    FeedbackRequest, FeedbackResponse, LogItem,
    ProfessorConfirmRequest
)
from agents.chat_agent import ChatAgent
from memory.memory_store import MemoryStore
from ingestion.ingest_pipeline import IngestPipeline

router = APIRouter()
chat_agent = ChatAgent()
memory = MemoryStore()
ingest_pipeline = IngestPipeline()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Conversational endpoint routing to RAG, collaboration or gap analysis."""
    try:
        res = chat_agent.run_query(request.query, role=request.role)
        # Log to memory database automatically
        query_log_id = memory.log_query(
            query_text=request.query,
            response_text=res["response_text"],
            mode=res["intent"],
            role=request.role
        )
        res["data"]["query_log_id"] = query_log_id
        return ChatResponse(
            intent=res["intent"],
            response_text=res["response_text"],
            data=res["data"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload_pdf")
async def upload_pdf_endpoint(file: UploadFile = File(...)):
    """Uploads, cleans, chunks, and indexes a faculty profile PDF."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        # Create temp file
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        chunks_count = ingest_pipeline.ingest_pdf(temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        return {
            "filename": file.filename,
            "status": "success",
            "chunks_ingested": chunks_count,
            "message": f"Successfully ingested {chunks_count} chunks from {file.filename}."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommend", response_model=ChatResponse)
async def recommend_endpoint(request: ChatRequest):
    """Finds faculty matches based on research domains."""
    try:
        # Force standard RAG intent
        rag_res = chat_agent.rag.run(request.query)
        query_log_id = memory.log_query(
            query_text=request.query,
            response_text=rag_res["response_text"],
            mode="recommend"
        )
        # Save recommendations to database
        recs = []
        for match in rag_res["internal_matches"]:
            recs.append({
                "faculty_name": match["metadata"].get("source", "Unknown"),
                "reasoning": match["document"][:200] + "...",
                "is_fallback": rag_res["is_fallback_active"]
            })
        memory.log_recommendations(query_log_id, recs)
        
        rag_res["query_log_id"] = query_log_id
        return ChatResponse(
            intent="recommend",
            response_text=rag_res["response_text"],
            data=rag_res
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collaborate", response_model=CollaborateResponse)
async def collaborate_endpoint(request: CollaborateRequest):
    """Evaluates fit and synergy between two faculty members."""
    try:
        col_res = chat_agent.collaboration.suggest_collaboration(request.faculty_a, request.faculty_b)
        if not col_res.get("success"):
            raise HTTPException(status_code=400, detail=col_res.get("error"))
            
        # Log to memory database
        query_log_id = memory.log_query(
            query_text=f"Collaborate: {request.faculty_a} and {request.faculty_b}",
            response_text=col_res["full_response"],
            mode="collaborate"
        )
        memory.log_collaborations(query_log_id, [{
            "faculty_a": request.faculty_a,
            "faculty_b": request.faculty_b,
            "synergy_reason": col_res["full_response"],
            "project_idea": col_res["full_response"]
        }])
        
        return CollaborateResponse(
            faculty_a=request.faculty_a,
            faculty_b=request.faculty_b,
            synergy_reason=col_res["full_response"],
            project_idea=col_res["full_response"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/professor-mode", response_model=ProfessorModeResponse)
async def professor_mode_endpoint(request: ProfessorModeRequest):
    """Gap analysis comparing local capabilities vs global research trends."""
    try:
        prof_res = chat_agent.professor.analyze_gaps(request.topic)
        
        query_log_id = memory.log_query(
            query_text=f"Professor Mode: {request.topic}",
            response_text=prof_res["analysis"],
            mode="professor"
        )
        
        return ProfessorModeResponse(
            topic=request.topic,
            analysis=prof_res["analysis"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/professor/analyze")
async def professor_analyze_endpoint(request: ProfessorModeRequest):
    """Production-grade Professor Mode analysis (Trends, Gaps, Workloads, Projects)."""
    try:
        from professor_mode.professor_agent import ProfessorAgent
        prof_agent = ProfessorAgent()
        report = prof_agent.run_analysis_report(request.topic)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/professor/confirm")
async def professor_confirm_endpoint(request: ProfessorConfirmRequest):
    """Action Layer: Logs the selected project and generates academic email draft."""
    try:
        from professor_mode.professor_agent import ProfessorAgent
        prof_agent = ProfessorAgent()
        
        # 1. Log to DB
        q_log_id = prof_agent.log_recommendation_to_db(
            topic=request.topic,
            report=request.report,
            project_idx=request.project_idx
        )
        if q_log_id == -1:
            raise HTTPException(status_code=500, detail="Failed to log recommendation.")

        # 2. Get selected project
        projects = request.report.get("project_suggestions", [])
        if not (0 <= request.project_idx < len(projects)):
            raise HTTPException(status_code=400, detail="Invalid project selection index.")
        selected_proj = projects[request.project_idx]

        # 3. Generate email
        email_draft = prof_agent.generate_collaboration_email(selected_proj)

        # 4. Trigger Email Service to send/mock-send
        from services.email_service import EmailService
        recipients = [f"{fac.replace(' ', '.').lower()}@university.edu" for fac in selected_proj.get("faculty", [])]
        if not recipients:
            recipients = ["coordinator@university.edu"]
        EmailService.send_pitch(
            subject=email_draft["subject"],
            body=email_draft["body"],
            recipients=recipients
        )

        return {
            "status": "success",
            "query_log_id": q_log_id,
            "email_draft": email_draft
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback", response_model=FeedbackResponse)
async def feedback_endpoint(request: FeedbackRequest):
    """Allows user feedback logging for queries."""
    success = memory.log_user_feedback(
        query_log_id=request.query_log_id,
        rating=request.rating,
        comments=request.comments
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to record feedback.")
    return FeedbackResponse(success=True, message="Feedback logged successfully.")

@router.get("/logs", response_model=List[LogItem])
async def logs_endpoint(role: Optional[str] = None):
    """Fetch audit history logs, optionally filtered by role."""
    logs = memory.get_recent_logs(role=role)
    return [LogItem(**log) for log in logs]

@router.get("/stats")
async def stats_endpoint():
    """Dashboard statistics: faculty, papers, queries, domains."""
    try:
        import chromadb, os
        from core.config import settings

        # ChromaDB stats
        client = chromadb.CloudClient(
            api_key=settings.CHROMA_API_KEY,
            tenant=settings.CHROMA_TENANT,
            database=settings.CHROMA_DATABASE,
        )
        col = client.get_or_create_collection(settings.CHROMA_COLLECTION_NAME)
        chunk_count = col.count()

        # Get distinct sources from ChromaDB
        sample = col.get(limit=300, include=["metadatas"])
        sources = {}
        for m in sample["metadatas"]:
            src = m.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        paper_count = len(sources)

        # Map paper names to faculty
        faculty_map = {
            "PADMAJA": "Plant Disease / Agriculture AI",
            "VENKATESHWARA": "Feature Engineering / ML",
            "venkateshwara": "Feature Engineering / ML",
            "MADHURYA": "IoT / Networking",
            "GAGANDEEP": "IoT / Healthcare",
            "gagandeep": "IoT / Healthcare",
            "VASANTHA": "Network Infrastructure",
            "vasantha": "Network Infrastructure",
            "SRININVAS_GONGULA": "Big Data / Safety",
            "RAVIKUMAR": "Networking / IPv6",
            "MANZOOR": "Deep Learning / GenAI",
        }
        domains = [
            "Agriculture AI", "Machine Learning", "IoT", "Healthcare",
            "Big Data", "Networking", "Deep Learning", "Generative AI",
            "Economics", "Heart Disease Research", "Computer Vision"
        ]

        # Query log stats
        logs = memory.get_recent_logs(limit=100)
        total_queries = len(logs)
        intent_counts = {}
        for log in logs:
            mode = log.get("mode", "rag")
            intent_counts[mode] = intent_counts.get(mode, 0) + 1

        return {
            "chunk_count": chunk_count,
            "paper_count": paper_count,
            "faculty_count": 8,
            "domain_count": len(domains),
            "total_queries": total_queries,
            "domains": domains,
            "papers": list(sources.keys()),
            "intent_breakdown": intent_counts,
            "model": settings.GROQ_MODEL.split("/")[-1],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

