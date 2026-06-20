from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


# ── Single message ────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str                          # "user" | "model"
    parts: str                         # actual message text
    type: str = "chat"                 # "chat" | "document_draft" | "action"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # sirf email draft ke liye, baaki None rahega
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


# ── Ek poori session (ek conversation thread) ─────────────────────
class ChatSession(BaseModel):
    session_id: str
    user_id: str
    preview: str = "New conversation"  # last user message (40 chars)
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)


# ── API Request/Response schemas ──────────────────────────────────
class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None   # None ho to naya session banega


class NewSessionResponse(BaseModel):
    session_id: str
    created_at: datetime


class SessionSummary(BaseModel):
    session_id: str
    preview: str
    created_at: datetime
    last_message_at: datetime


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]