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
    ProfessorConfirmRequest,
    PaperChatCreate, PaperChatResponse,
    FacultyChatCreate, FacultyChatResponse,
    AnnouncementCreate, AnnouncementResponse
)
from agents.chat_agent import ChatAgent
from memory.memory_store import MemoryStore
from ingestion.ingest_pipeline import IngestPipeline
from core.logger import logger

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
        if os.path.exists(temp_path):
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
    try:
        logs = memory.get_recent_logs(role=role)
        return [LogItem(**log) for log in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def stats_endpoint():
    """Dashboard statistics: faculty, papers, queries, domains."""
    try:
        import chromadb
        from core.config import settings

        # ChromaDB stats (wrapped in try-catch to prevent dashboard crash on DB connection failure)
        chunk_count = 0
        paper_count = 0
        papers_list = []
        try:
            mode = os.getenv("CHROMA_MODE", "remote").strip().lower()
            if mode == "remote":
                client = chromadb.CloudClient(
                    api_key=settings.CHROMA_API_KEY,
                    tenant=settings.CHROMA_TENANT,
                    database=settings.CHROMA_DATABASE,
                )
            else:
                persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chromadb_data")
                client = chromadb.PersistentClient(path=persist_dir)

            col = client.get_or_create_collection(settings.CHROMA_COLLECTION_NAME)
            chunk_count = col.count()

            # Get distinct sources from ChromaDB
            sample = col.get(limit=300, include=["metadatas"])
            sources = {}
            for m in sample["metadatas"]:
                src = m.get("source", "unknown")
                sources[src] = sources.get(src, 0) + 1

            paper_count = len(sources)
            papers_list = list(sources.keys())
        except Exception as chroma_err:
            logger.error(f"ChromaDB statistics loading failed: {chroma_err}")
            # Keep default fallback values (0) so the rest of dashboard can load

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
            "papers": papers_list,
            "intent_breakdown": intent_counts,
            "model": settings.GROQ_MODEL.split("/")[-1],
        }
    except Exception as e:
        logger.error(f"General statistics loading failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paper-chat", response_model=PaperChatResponse)
async def post_paper_chat(request: PaperChatCreate):
    """Saves a student-teacher discussion message to Supabase/DB."""
    try:
        from services.supabase_service import SupabaseService
        res = SupabaseService.save_message(
            paper_title=request.paper_title,
            sender_name=request.sender_name,
            sender_role=request.sender_role,
            message=request.message
        )
        return PaperChatResponse(
            id=res.get("id"),
            paper_title=res["paper_title"],
            sender_name=res["sender_name"],
            sender_role=res["sender_role"],
            message=res["message"],
            timestamp=str(res["timestamp"])
        )
    except Exception as e:
        logger.error(f"Failed to post paper chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper-chat", response_model=List[PaperChatResponse])
async def get_paper_chats(paper_title: str):
    """Retrieves all chat messages for a specific research paper."""
    try:
        from services.supabase_service import SupabaseService
        messages = SupabaseService.get_messages(paper_title=paper_title)
        return [
            PaperChatResponse(
                id=m.get("id"),
                paper_title=m["paper_title"],
                sender_name=m["sender_name"],
                sender_role=m["sender_role"],
                message=m["message"],
                timestamp=str(m["timestamp"])
            )
            for m in messages
        ]
    except Exception as e:
        logger.error(f"Failed to fetch paper chats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────
# Faculty Direct Chat (Student → Faculty DMs)
# ─────────────────────────────────────────────────────────────────

@router.post("/faculty-chat", response_model=FacultyChatResponse)
async def post_faculty_chat(request: FacultyChatCreate):
    """Saves a direct student-to-faculty chat message."""
    try:
        from services.supabase_service import SupabaseService
        res = SupabaseService.save_faculty_message(
            faculty_name=request.faculty_name,
            sender_name=request.sender_name,
            sender_role=request.sender_role,
            message=request.message
        )
        return FacultyChatResponse(
            id=res.get("id"),
            faculty_name=res["faculty_name"],
            sender_name=res["sender_name"],
            sender_role=res["sender_role"],
            message=res["message"],
            timestamp=str(res["timestamp"])
        )
    except Exception as e:
        logger.error(f"Failed to post faculty chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faculty-chat", response_model=List[FacultyChatResponse])
async def get_faculty_chats(faculty_name: str):
    """Retrieves all chat messages for a specific faculty member."""
    try:
        from services.supabase_service import SupabaseService
        messages = SupabaseService.get_faculty_messages(faculty_name=faculty_name)
        return [
            FacultyChatResponse(
                id=m.get("id"),
                faculty_name=m["faculty_name"],
                sender_name=m["sender_name"],
                sender_role=m["sender_role"],
                message=m["message"],
                timestamp=str(m["timestamp"])
            )
            for m in messages
        ]
    except Exception as e:
        logger.error(f"Failed to fetch faculty chats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faculty-chat/all")
async def get_all_faculty_chats():
    """Retrieves all faculty chat threads grouped by faculty name (for faculty inbox view)."""
    try:
        from db.database import SessionLocal
        from db.models import FacultyChat
        from sqlalchemy import func

        db = SessionLocal()
        try:
            threads = (
                db.query(
                    FacultyChat.faculty_name,
                    func.count(FacultyChat.id).label("message_count"),
                    func.max(FacultyChat.timestamp).label("last_message_at")
                )
                .group_by(FacultyChat.faculty_name)
                .order_by(func.max(FacultyChat.timestamp).desc())
                .all()
            )
            return [
                {
                    "faculty_name": t.faculty_name,
                    "message_count": t.message_count,
                    "last_message_at": t.last_message_at.isoformat() if t.last_message_at else None
                }
                for t in threads
            ]
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to fetch all faculty chat threads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────
# Faculty Announcements (Broadcasting System)
# ─────────────────────────────────────────────────────────────────

@router.post("/announcements", response_model=AnnouncementResponse)
async def post_announcement(request: AnnouncementCreate):
    """Saves a new faculty announcement to the database."""
    try:
        from db.database import SessionLocal
        from db.models import Announcement
        
        db = SessionLocal()
        try:
            announcement = Announcement(
                title=request.title,
                content=request.content,
                faculty_name=request.faculty_name,
                category=request.category,
                priority=request.priority,
                attachment=request.attachment,
                target_audience=request.target_audience,
                target_dept=request.target_dept,
                target_year=request.target_year,
                target_sec=request.target_sec,
                expiry_date=request.expiry_date,
                status=request.status
            )
            db.add(announcement)
            db.commit()
            db.refresh(announcement)
            return AnnouncementResponse(
                id=announcement.id,
                title=announcement.title,
                content=announcement.content,
                faculty_name=announcement.faculty_name,
                timestamp=announcement.timestamp.isoformat(),
                category=announcement.category,
                priority=announcement.priority,
                attachment=announcement.attachment,
                target_audience=announcement.target_audience,
                target_dept=announcement.target_dept,
                target_year=announcement.target_year,
                target_sec=announcement.target_sec,
                expiry_date=announcement.expiry_date,
                status=announcement.status
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to post announcement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/announcements", response_model=List[AnnouncementResponse])
async def get_announcements(
    role: Optional[str] = None,
    department: Optional[str] = None,
    year: Optional[str] = None,
    section: Optional[str] = None
):
    """Retrieves all announcements sorted by timestamp descending, with optional filtering for students."""
    try:
        from db.database import SessionLocal
        from db.models import Announcement
        from datetime import datetime, timezone

        db = SessionLocal()
        try:
            query = db.query(Announcement)
            if role == "student":
                query = query.filter(Announcement.status == "published")
                
            announcements = (
                query.order_by(Announcement.timestamp.desc())
                .all()
            )
            
            filtered = []
            current_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            for a in announcements:
                # Expiry check
                if role == "student" and a.expiry_date:
                    if a.expiry_date < current_date_str:
                        continue
                
                # Target audience match check
                if role == "student":
                    if a.target_audience == "Department" and department:
                        if a.target_dept and a.target_dept.lower() != department.lower():
                            continue
                    elif a.target_audience == "Year" and year:
                        if a.target_dept and a.target_dept.lower() != department.lower():
                            continue
                        if a.target_year and a.target_year.lower() != year.lower():
                            continue
                    elif a.target_audience == "Section" and section:
                        if a.target_dept and a.target_dept.lower() != department.lower():
                            continue
                        if a.target_year and a.target_year.lower() != year.lower():
                            continue
                        if a.target_sec and a.target_sec.lower() != section.lower():
                            continue
                    elif a.target_audience == "All":
                        pass
                    else:
                        if a.target_audience in ("Department", "Year", "Section"):
                            continue

                filtered.append(
                    AnnouncementResponse(
                        id=a.id,
                        title=a.title,
                        content=a.content,
                        faculty_name=a.faculty_name,
                        timestamp=a.timestamp.isoformat(),
                        category=a.category,
                        priority=a.priority,
                        attachment=a.attachment,
                        target_audience=a.target_audience,
                        target_dept=a.target_dept,
                        target_year=a.target_year,
                        target_sec=a.target_sec,
                        expiry_date=a.expiry_date,
                        status=a.status
                    )
                )
            return filtered
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to fetch announcements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/announcements/{id}", response_model=AnnouncementResponse)
async def put_announcement(id: int, request: AnnouncementCreate):
    """Updates an existing faculty announcement."""
    try:
        from db.database import SessionLocal
        from db.models import Announcement
        
        db = SessionLocal()
        try:
            announcement = db.query(Announcement).filter(Announcement.id == id).first()
            if not announcement:
                raise HTTPException(status_code=404, detail="Announcement not found")
            
            announcement.title = request.title
            announcement.content = request.content
            announcement.faculty_name = request.faculty_name
            announcement.category = request.category
            announcement.priority = request.priority
            announcement.attachment = request.attachment
            announcement.target_audience = request.target_audience
            announcement.target_dept = request.target_dept
            announcement.target_year = request.target_year
            announcement.target_sec = request.target_sec
            announcement.expiry_date = request.expiry_date
            announcement.status = request.status
            
            db.commit()
            db.refresh(announcement)
            return AnnouncementResponse(
                id=announcement.id,
                title=announcement.title,
                content=announcement.content,
                faculty_name=announcement.faculty_name,
                timestamp=announcement.timestamp.isoformat(),
                category=announcement.category,
                priority=announcement.priority,
                attachment=announcement.attachment,
                target_audience=announcement.target_audience,
                target_dept=announcement.target_dept,
                target_year=announcement.target_year,
                target_sec=announcement.target_sec,
                expiry_date=announcement.expiry_date,
                status=announcement.status
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update announcement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/announcements/{id}")
async def delete_announcement(id: int):
    """Deletes an announcement from the database."""
    try:
        from db.database import SessionLocal
        from db.models import Announcement
        
        db = SessionLocal()
        try:
            announcement = db.query(Announcement).filter(Announcement.id == id).first()
            if not announcement:
                raise HTTPException(status_code=404, detail="Announcement not found")
            
            db.delete(announcement)
            db.commit()
            return {"status": "success", "message": "Announcement deleted successfully"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete announcement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/announcements/upload_attachment")
async def upload_attachment_endpoint(file: UploadFile = File(...)):
    """Uploads an optional attachment file to the static/uploads/ directory."""
    try:
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        safe_filename = os.path.basename(file.filename)
        dest_path = os.path.join(uploads_dir, safe_filename)
        
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_url = f"/static/uploads/{safe_filename}"
        return {"status": "success", "url": file_url}
    except Exception as e:
        logger.error(f"Failed to upload attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

