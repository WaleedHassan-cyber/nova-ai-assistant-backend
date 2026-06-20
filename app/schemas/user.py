from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class User(BaseModel):
    username: str
    email: EmailStr
    password: Optional[str] = None
    provider: str = "email"
    google_id: Optional[str] = None
    fcm_token: Optional[str] = None
    otp: Optional[str] = None
    otp_expiry: Optional[datetime] = None
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # ✅ New fields (yahi sirf add karne hain)
    profile_pic_url: Optional[str] = None       # Cloud URL (Cloudinary/Firebase)
    pending_avatar_path: Optional[str] = None   # Flutter local path (sync ke liye)
    log_alerts: bool = False
    is2FAEnabled: bool = False