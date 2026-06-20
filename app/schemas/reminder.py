from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# 1. Combined Task Schema (For both Todo & Reminder)
class TaskSchema(BaseModel):
    id: str = Field(..., example="user123_17000000")  # Flutter ki unique ID
    notificationId: Optional[int] = None  # Reminders ke liye zaroori hai
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    type: str = Field(..., example="reminder")  # 'todo' ya 'reminder'
    status: str = Field(default="pending")  # 'pending' ya 'completed'
    isCompleted: bool = Field(default=False)

    # Dates
    remindAt: Optional[datetime] = None  # Sirf reminders ke liye
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# 2. Bulk Sync Request (List of Tasks)
class SyncRequest(BaseModel):
    tasks: list[TaskSchema]


# 3. Bulk Delete Request
class DeleteRequest(BaseModel):
    ids: list[str]