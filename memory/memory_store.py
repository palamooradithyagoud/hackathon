"""
Persistent Memory Store.
Saves queries, recommendations, collaborations, projects, and feedback to both database and JSONL backup logs.
"""

from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import QueryLog, Recommendation, Collaboration, ProjectSuggestion, Feedback
from core.logger import logger, log_decision, log_feedback

class MemoryStore:
    def __init__(self):
        pass

    def log_query(self, query_text: str, response_text: str, mode: str = "chat", role: str = "student") -> int:
        """Logs a conversation query and returns the record ID."""
        db: Session = SessionLocal()
        try:
            query_log = QueryLog(
                query_text=query_text,
                response_text=response_text,
                mode=mode,
                role=role
            )
            db.add(query_log)
            db.commit()
            db.refresh(query_log)
            
            # Backup to JSONL
            log_decision({
                "action": "query_logged",
                "id": query_log.id,
                "query": query_text,
                "mode": mode,
                "role": role
            })
            
            return query_log.id
        except Exception as e:
            logger.error(f"Failed to log query in database: {e}")
            db.rollback()
            return -1
        finally:
            db.close()

    def log_recommendations(self, query_log_id: int, recommendations: list[dict]) -> bool:
        """
        Logs faculty recommendations linked to a query.
        recommendations format: [{"faculty_name": "...", "reasoning": "...", "is_fallback": False}]
        """
        if query_log_id == -1:
            return False
            
        db: Session = SessionLocal()
        try:
            for rec in recommendations:
                db_rec = Recommendation(
                    query_log_id=query_log_id,
                    faculty_name=rec["faculty_name"],
                    reasoning=rec["reasoning"],
                    is_fallback=rec.get("is_fallback", False)
                )
                db.add(db_rec)
                
            db.commit()
            
            # Backup to JSONL
            log_decision({
                "action": "recommendations_logged",
                "query_log_id": query_log_id,
                "recommendations": recommendations
            })
            return True
        except Exception as e:
            logger.error(f"Failed to log recommendations: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def log_collaborations(self, query_log_id: int, collaborations: list[dict]) -> bool:
        """
        Logs collaboration recommendations linked to a query.
        collaborations format: [{"faculty_a": "...", "faculty_b": "...", "synergy_reason": "...", "project_idea": "..."}]
        """
        if query_log_id == -1:
            return False
            
        db: Session = SessionLocal()
        try:
            for col in collaborations:
                db_col = Collaboration(
                    query_log_id=query_log_id,
                    faculty_a=col["faculty_a"],
                    faculty_b=col["faculty_b"],
                    synergy_reason=col["synergy_reason"],
                    project_idea=col["project_idea"]
                )
                db.add(db_col)
                
            db.commit()
            
            # Backup to JSONL
            log_decision({
                "action": "collaborations_logged",
                "query_log_id": query_log_id,
                "collaborations": collaborations
            })
            return True
        except Exception as e:
            logger.error(f"Failed to log collaborations: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def log_projects(self, query_log_id: int, projects: list[dict]) -> bool:
        """
        Logs project suggestions linked to a query.
        projects format: [{"title": "...", "description": "...", "target_faculty": "..."}]
        """
        if query_log_id == -1:
            return False
            
        db: Session = SessionLocal()
        try:
            for proj in projects:
                db_proj = ProjectSuggestion(
                    query_log_id=query_log_id,
                    title=proj["title"],
                    description=proj["description"],
                    target_faculty=proj.get("target_faculty", "")
                )
                db.add(db_proj)
                
            db.commit()
            
            # Backup to JSONL
            log_decision({
                "action": "projects_logged",
                "query_log_id": query_log_id,
                "projects": projects
            })
            return True
        except Exception as e:
            logger.error(f"Failed to log projects: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def log_user_feedback(self, query_log_id: int, rating: int | None, comments: str | None) -> bool:
        """Logs user feedback for a query and query response."""
        db: Session = SessionLocal()
        try:
            db_feedback = Feedback(
                query_log_id=query_log_id,
                rating=rating,
                comments=comments
            )
            db.add(db_feedback)
            db.commit()
            
            # Backup to JSONL
            log_feedback({
                "query_log_id": query_log_id,
                "rating": rating,
                "comments": comments
            })
            return True
        except Exception as e:
            logger.error(f"Failed to log feedback: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def get_recent_logs(self, limit: int = 20, role: str = None) -> list[dict]:
        """Fetches recent query logs and responses, optionally filtered by role."""
        db: Session = SessionLocal()
        try:
            query = db.query(QueryLog)
            if role:
                query = query.filter(QueryLog.role == role)
            logs = query.order_by(QueryLog.timestamp.desc()).limit(limit).all()
            result = []
            for log in logs:
                result.append({
                    "id": log.id,
                    "query": log.query_text,
                    "response": log.response_text,
                    "mode": log.mode,
                    "role": log.role,
                    "timestamp": log.timestamp.isoformat()
                })
            return result
        except Exception as e:
            logger.error(f"Failed to fetch logs: {e}")
            return []
        finally:
            db.close()
