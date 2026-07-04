"""
Flask Routes Blueprint.
Declares endpoints for chat, upload, collaboration, gap analysis, logs, and feedback.
"""

import os
import shutil
import tempfile
from typing import List, Optional
from flask import Blueprint, request, jsonify, abort
from pydantic import ValidationError

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

api_blueprint = Blueprint("api", __name__)
chat_agent = ChatAgent()
memory = MemoryStore()
ingest_pipeline = IngestPipeline()

@api_blueprint.route("/chat", methods=["POST"])
async def chat_endpoint():
    """Conversational endpoint routing to RAG, collaboration or gap analysis."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "Missing JSON request body"}), 400
            
        try:
            req_data = ChatRequest.model_validate(data)
        except ValidationError as ve:
            return jsonify({"detail": ve.errors()}), 422
            
        res = chat_agent.run_query(req_data.query, role=req_data.role)
        # Log to memory database automatically
        query_log_id = memory.log_query(
            query_text=req_data.query,
            response_text=res["response_text"],
            mode=res["intent"],
            role=req_data.role
        )
        res["data"]["query_log_id"] = query_log_id
        
        resp_schema = ChatResponse(
            intent=res["intent"],
            response_text=res["response_text"],
            data=res["data"]
        )
        return jsonify(resp_schema.model_dump())
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/upload_pdf", methods=["POST"])
async def upload_pdf_endpoint():
    """Uploads, cleans, chunks, and indexes a faculty profile PDF."""
    if "file" not in request.files:
        return jsonify({"detail": "No file part in the request"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"detail": "No file selected for uploading"}), 400
        
    if not file.filename.endswith(".pdf"):
        return jsonify({"detail": "Only PDF files are supported."}), 400
        
    try:
        # Create temp file
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        
        file.save(temp_path)
            
        chunks_count = ingest_pipeline.ingest_pdf(temp_path)
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({
            "filename": file.filename,
            "status": "success",
            "chunks_ingested": chunks_count,
            "message": f"Successfully ingested {chunks_count} chunks from {file.filename}."
        })
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/recommend", methods=["POST"])
async def recommend_endpoint():
    """Finds faculty matches based on research domains."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "Missing JSON request body"}), 400
            
        try:
            req_data = ChatRequest.model_validate(data)
        except ValidationError as ve:
            return jsonify({"detail": ve.errors()}), 422
            
        # Force standard RAG intent
        rag_res = chat_agent.rag.run(req_data.query)
        query_log_id = memory.log_query(
            query_text=req_data.query,
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
        
        resp_schema = ChatResponse(
            intent="recommend",
            response_text=rag_res["response_text"],
            data=rag_res
        )
        return jsonify(resp_schema.model_dump())
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/collaborate", methods=["POST"])
async def collaborate_endpoint():
    """Evaluates fit and synergy between two faculty members."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "Missing JSON request body"}), 400
            
        try:
            req_data = CollaborateRequest.model_validate(data)
        except ValidationError as ve:
            return jsonify({"detail": ve.errors()}), 422
            
        col_res = chat_agent.collaboration.suggest_collaboration(req_data.faculty_a, req_data.faculty_b)
        if not col_res.get("success"):
            return jsonify({"detail": col_res.get("error")}), 400
            
        # Log to memory database
        query_log_id = memory.log_query(
            query_text=f"Collaborate: {req_data.faculty_a} and {req_data.faculty_b}",
            response_text=col_res["full_response"],
            mode="collaborate"
        )
        memory.log_collaborations(query_log_id, [{
            "faculty_a": req_data.faculty_a,
            "faculty_b": req_data.faculty_b,
            "synergy_reason": col_res["full_response"],
            "project_idea": col_res["full_response"]
        }])
        
        resp_schema = CollaborateResponse(
            faculty_a=req_data.faculty_a,
            faculty_b=req_data.faculty_b,
            synergy_reason=col_res["full_response"],
            project_idea=col_res["full_response"]
        )
        return jsonify(resp_schema.model_dump())
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/professor-mode", methods=["POST"])
async def professor_mode_endpoint():
    """Gap analysis comparing local capabilities vs global research trends."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "Missing JSON request body"}), 400
            
        try:
            req_data = ProfessorModeRequest.model_validate(data)
        except ValidationError as ve:
            return jsonify({"detail": ve.errors()}), 422
            
        prof_res = chat_agent.professor.analyze_gaps(req_data.topic)
        
        query_log_id = memory.log_query(
            query_text=f"Professor Mode: {req_data.topic}",
            response_text=prof_res["analysis"],
            mode="professor"
        )
        
        resp_schema = ProfessorModeResponse(
            topic=req_data.topic,
            analysis=prof_res["analysis"]
        )
        return jsonify(resp_schema.model_dump())
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/professor/analyze", methods=["POST"])
async def professor_analyze_endpoint():
    """Production-grade Professor Mode analysis (Trends, Gaps, Workloads, Projects)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "Missing JSON request body"}), 400
            
        try:
            req_data = ProfessorModeRequest.model_validate(data)
        except ValidationError as ve:
            return jsonify({"detail": ve.errors()}), 422
            
        from professor_mode.professor_agent import ProfessorAgent
        prof_agent = ProfessorAgent()
        report = prof_agent.run_analysis_report(req_data.topic)
        return jsonify(report)
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/professor/confirm", methods=["POST"])
async def professor_confirm_endpoint():
    """Action Layer: Logs the selected project and generates academic email draft."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "Missing JSON request body"}), 400
            
        try:
            req_data = ProfessorConfirmRequest.model_validate(data)
        except ValidationError as ve:
            return jsonify({"detail": ve.errors()}), 422
            
        from professor_mode.professor_agent import ProfessorAgent
        prof_agent = ProfessorAgent()
        
        # 1. Log to DB
        q_log_id = prof_agent.log_recommendation_to_db(
            topic=req_data.topic,
            report=req_data.report,
            project_idx=req_data.project_idx
        )
        if q_log_id == -1:
            return jsonify({"detail": "Failed to log recommendation."}), 500

        # 2. Get selected project
        projects = req_data.report.get("project_suggestions", [])
        if not (0 <= req_data.project_idx < len(projects)):
            return jsonify({"detail": "Invalid project selection index."}), 400
        selected_proj = projects[req_data.project_idx]

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

        return jsonify({
            "status": "success",
            "query_log_id": q_log_id,
            "email_draft": email_draft
        })
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/feedback", methods=["POST"])
async def feedback_endpoint():
    """Allows user feedback logging for queries."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "Missing JSON request body"}), 400
            
        try:
            req_data = FeedbackRequest.model_validate(data)
        except ValidationError as ve:
            return jsonify({"detail": ve.errors()}), 422
            
        success = memory.log_user_feedback(
            query_log_id=req_data.query_log_id,
            rating=req_data.rating,
            comments=req_data.comments
        )
        if not success:
            return jsonify({"detail": "Failed to record feedback."}), 400
            
        resp_schema = FeedbackResponse(success=True, message="Feedback logged successfully.")
        return jsonify(resp_schema.model_dump())
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/logs", methods=["GET"])
async def logs_endpoint():
    """Fetch audit history logs, optionally filtered by role."""
    try:
        role = request.args.get("role")
        logs = memory.get_recent_logs(role=role)
        return jsonify([LogItem(**log).model_dump() for log in logs])
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@api_blueprint.route("/stats", methods=["GET"])
async def stats_endpoint():
    """Dashboard statistics: faculty, papers, queries, domains."""
    try:
        import chromadb
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

        return jsonify({
            "chunk_count": chunk_count,
            "paper_count": paper_count,
            "faculty_count": 8,
            "domain_count": len(domains),
            "total_queries": total_queries,
            "domains": domains,
            "papers": list(sources.keys()),
            "intent_breakdown": intent_counts,
            "model": settings.GROQ_MODEL.split("/")[-1],
        })
    except Exception as e:
        return jsonify({"detail": str(e)}), 500
