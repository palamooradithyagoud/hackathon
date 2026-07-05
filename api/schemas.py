"""
Pydantic API request/response schemas.
"""

from typing import Optional, Any
from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: str
    role: Optional[str] = "student"

class ChatResponse(BaseModel):
    intent: str
    response_text: str
    data: dict

class CollaborateRequest(BaseModel):
    faculty_a: str
    faculty_b: str

class CollaborateResponse(BaseModel):
    faculty_a: str
    faculty_b: str
    synergy_reason: str
    project_idea: str

class ProfessorModeRequest(BaseModel):
    topic: str

class ProfessorModeResponse(BaseModel):
    topic: str
    analysis: str

class FeedbackRequest(BaseModel):
    query_log_id: int
    rating: int
    comments: Optional[str] = None

class FeedbackResponse(BaseModel):
    success: bool
    message: str

class LogItem(BaseModel):
    id: int
    query: str
    response: str
    mode: str
    role: Optional[str] = None
    timestamp: str

class ProfessorConfirmRequest(BaseModel):
    topic: str
    report: dict
    project_idx: int


class PaperChatCreate(BaseModel):
    paper_title: str
    sender_name: str
    sender_role: str
    message: str


class PaperChatResponse(BaseModel):
    id: Optional[int] = None
    paper_title: str
    sender_name: str
    sender_role: str
    message: str
    timestamp: str


class FacultyChatCreate(BaseModel):
    faculty_name: str
    sender_name: str
    sender_role: str
    message: str


class FacultyChatResponse(BaseModel):
    id: Optional[int] = None
    faculty_name: str
    sender_name: str
    sender_role: str
    message: str
    timestamp: str


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    faculty_name: str
    category: Optional[str] = None
    priority: Optional[str] = "Low"
    attachment: Optional[str] = None
    target_audience: Optional[str] = "All"
    target_dept: Optional[str] = None
    target_year: Optional[str] = None
    target_sec: Optional[str] = None
    expiry_date: Optional[str] = None
    status: Optional[str] = "published"


class AnnouncementResponse(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    faculty_name: str
    timestamp: str
    category: Optional[str] = None
    priority: Optional[str] = "Low"
    attachment: Optional[str] = None
    target_audience: Optional[str] = "All"
    target_dept: Optional[str] = None
    target_year: Optional[str] = None
    target_sec: Optional[str] = None
    expiry_date: Optional[str] = None
    status: Optional[str] = "published"


