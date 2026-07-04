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
