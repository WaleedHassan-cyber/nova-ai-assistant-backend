from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TaskSyncSchema(BaseModel):
    id: str
    # Flutter se 'userId' aayega, lekin DB mein 'user_id' save hota hai
    userId: str = Field(..., alias="userId", validation_alias="user_id")

    # Notification sync ke liye
    notificationId: Optional[int] = Field(None, alias="notificationId", validation_alias="notification_id")

    title: str
    type: str  # 'todo' ya 'reminder'
    status: str

    # Flutter: isCompleted | DB: is_completed
    isCompleted: bool = Field(..., alias="isCompleted", validation_alias="is_completed")

    # Flutter: createdAt | DB: created_at
    createdAt: datetime = Field(..., alias="createdAt", validation_alias="created_at")

    # Flutter: remindAt | DB: remind_at
    remindAt: Optional[datetime] = Field(None, alias="remindAt", validation_alias="remind_at")

    class Config:
        populate_by_name = True