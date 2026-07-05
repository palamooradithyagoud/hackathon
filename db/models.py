"""
SQLAlchemy database models for persistence.
Stores user queries, recommendations, collaborations, projects, feedback, and logs.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from db.database import Base

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(String(500), nullable=False)
    response_text = Column(Text, nullable=False)
    mode = Column(String(50), default="chat")        # chat, collaborate, professor, etc.
    role = Column(String(50), default="student")     # student, faculty
    session_id = Column(String(100), nullable=True)  # browser session identifier
    sources_used = Column(JSON, nullable=True)        # list of paper sources cited
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    recommendations = relationship("Recommendation", back_populates="query_log", cascade="all, delete-orphan")
    collaborations = relationship("Collaboration", back_populates="query_log", cascade="all, delete-orphan")
    projects = relationship("ProjectSuggestion", back_populates="query_log", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="query_log", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="query_log", cascade="all, delete-orphan")


class ChatMessage(Base):
    """
    Stores individual chat turns (user message + AI reply) for a session.
    Linked to the parent QueryLog entry. Both student and faculty messages
    are stored here in Supabase.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    query_log_id = Column(Integer, ForeignKey("query_logs.id"), nullable=True)
    session_id = Column(String(100), nullable=True, index=True)  # browser session
    role = Column(String(50), nullable=False)             # 'student' or 'faculty'
    sender = Column(String(20), nullable=False)           # 'user' or 'assistant'
    message = Column(Text, nullable=False)                # actual message text
    intent = Column(String(50), nullable=True)            # rag, collaborate, professor
    paper_sources = Column(JSON, nullable=True)           # papers cited by the AI
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Link to query
    query_log = relationship("QueryLog", back_populates="messages")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    query_log_id = Column(Integer, ForeignKey("query_logs.id"))
    faculty_name = Column(String(200), nullable=False)
    reasoning = Column(Text, nullable=False)
    is_fallback = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Link to query
    query_log = relationship("QueryLog", back_populates="recommendations")


class Collaboration(Base):
    __tablename__ = "collaborations"

    id = Column(Integer, primary_key=True, index=True)
    query_log_id = Column(Integer, ForeignKey("query_logs.id"))
    faculty_a = Column(String(200), nullable=False)
    faculty_b = Column(String(200), nullable=False)
    synergy_reason = Column(Text, nullable=False)
    project_idea = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Link to query
    query_log = relationship("QueryLog", back_populates="collaborations")


class ProjectSuggestion(Base):
    __tablename__ = "project_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    query_log_id = Column(Integer, ForeignKey("query_logs.id"))
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    target_faculty = Column(String(500), nullable=True) # comma separated list
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Link to query
    query_log = relationship("QueryLog", back_populates="projects")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    query_log_id = Column(Integer, ForeignKey("query_logs.id"))
    rating = Column(Integer, nullable=True) # e.g. 1 to 5, or binary
    comments = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Link to query
    query_log = relationship("QueryLog", back_populates="feedback")


class FacultyWorkload(Base):
    __tablename__ = "faculty_workload"

    id = Column(Integer, primary_key=True, index=True)
    faculty_name = Column(String(200), nullable=False, unique=True)
    active_projects = Column(Integer, default=0)
    project_titles = Column(JSON, nullable=True)  # List of project title strings
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PaperEnrichment(Base):
    __tablename__ = "paper_enrichments"

    id = Column(Integer, primary_key=True, index=True)
    paper_title_key = Column(String(500), unique=True, index=True, nullable=False) # normalized title as key
    s2_paper_id = Column(String(100), nullable=True)
    doi = Column(String(100), nullable=True)
    venue = Column(String(200), nullable=True)
    year = Column(Integer, nullable=True)
    citation_count = Column(Integer, default=0)
    influential_citation_count = Column(Integer, default=0)
    authors = Column(Text, nullable=True) # comma-separated list of authors
    fields_of_study = Column(Text, nullable=True) # comma-separated list
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SemanticCache(Base):
    __tablename__ = "semantic_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(250), unique=True, index=True, nullable=False)
    response_json = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PaperChat(Base):
    """
    Stores student-teacher messages about a specific research paper.
    Persistent in Supabase with local SQLite fallback.
    """
    __tablename__ = "paper_chats"

    id = Column(Integer, primary_key=True, index=True)
    paper_title = Column(String(500), nullable=False, index=True)
    sender_name = Column(String(200), nullable=False)
    sender_role = Column(String(50), nullable=False)   # 'student' or 'faculty'
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class FacultyChat(Base):
    """
    Direct student-to-faculty messaging.
    A student picks a faculty member and sends messages directly.
    Faculty can see all messages sent to them and reply.
    Stored in Supabase with local SQLite fallback.
    """
    __tablename__ = "faculty_chats"

    id = Column(Integer, primary_key=True, index=True)
    faculty_name = Column(String(200), nullable=False, index=True)  # faculty being messaged
    sender_name = Column(String(200), nullable=False)               # who sent the message
    sender_role = Column(String(50), nullable=False)                # 'student' or 'faculty'
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class Announcement(Base):
    """
    Faculty announcements broadcast to students and other faculty.
    """
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    faculty_name = Column(String(200), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Expanded fields
    category = Column(String(100), nullable=True)
    priority = Column(String(50), default="Low")  # Low, Medium, High, Urgent
    attachment = Column(String(500), nullable=True)
    target_audience = Column(String(100), default="All")  # All, Department, Year, Section
    target_dept = Column(String(100), nullable=True)
    target_year = Column(String(100), nullable=True)
    target_sec = Column(String(100), nullable=True)
    expiry_date = Column(String(100), nullable=True)
    status = Column(String(50), default="published")  # draft, published



