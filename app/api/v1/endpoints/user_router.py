# app/api/v1/endpoints/user_router.py

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from bson import ObjectId
from app.core.db import db_connection
from app.core.config import settings
from app.api.v1.endpoints.deps import get_current_user

router = APIRouter()

# Cloudinary config (settings mein se aayega)
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    db = db_connection.db
    user_id = current_user["user_id"]

    # File type check
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")

    try:
        # File bytes padho
        contents = await file.read()

        # Cloudinary par upload karo
        result = cloudinary.uploader.upload(
            contents,
            folder="nova/avatars",
            public_id=f"user_{user_id}",  # Same user ka pic override hoga
            overwrite=True,
            resource_type="image"
        )

        url = result["secure_url"]

        # MongoDB update karo
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "profile_pic_url": url,
                "pending_avatar_path": None  # Sync complete, local path clear
            }}
        )

        return {
            "status": "success",
            "profile_pic_url": url
        }

    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Image upload failed")


