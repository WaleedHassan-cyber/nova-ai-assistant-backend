from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Dict
from app.core.db import db_connection
from app.schemas.sync import TaskSyncSchema
from app.api.v1.endpoints.deps import get_current_user
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


# --- 1. SYNC BULK (SECURED) ---
@router.post("/sync-bulk")
async def sync_bulk_tasks(
        tasks: List[TaskSyncSchema],
        current_user: dict = Depends(get_current_user)
):
    db = db_connection.db
    collection = db["reminders"]
    user_id = current_user["user_id"]

    try:
        synced_ids = []
        for task in tasks:
            # Note: Pydantic schema mein agar userId (camelCase) hai to wahi use karein
            # Hum hamesha token wala user_id force karenge taake koi aur data hack na kare
            await collection.update_one(
                {"id": task.id, "user_id": user_id},
                {"$set": {
                    "user_id": user_id,
                    "notification_id": task.notificationId,
                    "title": task.title,
                    "type": task.type,
                    "status": task.status,
                    "is_completed": task.isCompleted,
                    "created_at": task.createdAt,
                    "remind_at": task.remindAt if task.type == "reminder" else None,
                    "updated_at": datetime.now(timezone.utc)  # Timezone aware best practice
                }},
                upsert=True
            )
            synced_ids.append(task.id)

        return {
            "status": "success",
            "synced_count": len(synced_ids),
            "ids": synced_ids
        }

    except Exception as e:
        print(f"Sync Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error syncing tasks to database"
        )


# --- 2. DELETE BULK (SECURED) ---
@router.post("/delete-bulk")
async def delete_bulk_tasks(
        data: Dict[str, List[str]],
        current_user: dict = Depends(get_current_user)
):
    db = db_connection.db
    user_id = current_user["user_id"]
    ids_to_delete = data.get("ids", [])

    if not ids_to_delete:
        return {"status": "success", "message": "No IDs provided"}

    try:
        # Security Check: user_id lazmi hai taake koi dusre ki ID delete na kar de
        result = await db["reminders"].delete_many({
            "id": {"$in": ids_to_delete},
            "user_id": user_id
        })

        return {
            "status": "success",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# --- 3. GET TASKS / HYDRATION (SECURED) ---
@router.get("/tasks")
async def get_user_tasks(
        current_user: dict = Depends(get_current_user),
        limit: int = Query(1000, ge=1, le=5000),
        skip: int = 0
):
    try:
        db = db_connection.db
        user_id = current_user["user_id"]

        user_doc = await db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"profile_pic_url": 1, "username": 1, "_id": 0}
        )

        # ✅ Hum 'tasks' collection se hi fetch kar rahe hain
        cursor = db.reminders.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("updated_at", -1).skip(skip).limit(limit)

        tasks = await cursor.to_list(length=limit)

        formatted_tasks = []
        for t in tasks:
            # 🔥 CRITICAL FIX: Data ko Flutter LocalTask model ke mutabiq map karein
            formatted_tasks.append({
                "id": t.get("id"),
                "userId": t.get("user_id"),
                "title": t.get("title", ""),
                "type": t.get("type", "reminder"),
                "status": t.get("status", "pending"),
                "isCompleted": t.get("is_completed", False),  # snake_case to camelCase
                "notificationId": t.get("notification_id", 0),

                # Date Handle karein: Agar Mongo object hai toh string nikalain
                "remindAt": t["remind_at"].isoformat() if t.get("remind_at") and hasattr(t["remind_at"],
                                                                                         'isoformat') else None,
                "createdAt": t["created_at"].isoformat() if t.get("created_at") and hasattr(t["created_at"],
                                                                                            'isoformat') else None,
            })

        return {
            "status": "success",
            "profile_pic_url": user_doc.get("profile_pic_url") if user_doc else None,
            "username": user_doc.get("username") if user_doc else None,
            "tasks": formatted_tasks
        }
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")