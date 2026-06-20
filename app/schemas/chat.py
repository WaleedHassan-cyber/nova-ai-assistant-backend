from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

class ChatMessage(BaseModel):
    role: str  # "user" ya "model"
    parts: str # Asli message text
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Conversation(BaseModel):
    user_id: str
    messages: List[ChatMessage] = []
    last_updated: datetime = Field(default_factory=datetime.utcnow)

# YE ADD KAREIN: API Request handle karne ke liye
class ChatRequest(BaseModel):
    user_id: str
    message: str