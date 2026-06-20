# from datetime import datetime
#
# from fastapi import APIRouter, Body
#
# from app.core.db import db_connection
# # from app.schemas.reminder import ReminderCreate
#
# router = APIRouter()
#
#
# @router.post("/add")
# async def add_reminder(payload: ReminderCreate, user_id: str = Body(...)):
#     db = db_connection.db
#
#     new_reminder = {
#         "user_id": user_id,
#         "title": payload.title,
#         "description": payload.description,
#         "remind_at": payload.remind_at,
#         "status": "pending",
#         "is_notified": False,
#         "created_at": datetime.utcnow()
#     }
#
#     result = await db.reminders.insert_one(new_reminder)
#     return {"status": "success", "id": str(result.inserted_id)}
#
#
# @router.get("/list/{user_id}")
# async def list_reminders(user_id: str):
#     db = db_connection.db
#     # Indexing ki wajah se ye query aur sort boht fast hogi
#     cursor = db.reminders.find({"user_id": user_id}).sort("remind_at", 1)
#     reminders = await cursor.to_list(length=100)
#
#     for r in reminders:
#         r["id"] = str(r["_id"])
#         del r["_id"]
#
#     return reminders
#
# @router.get("/test-notification")
# async def manual_notify_test():
#     from app.services.scheduler import check_reminders
#     await check_reminders()
#     return {"status": "Triggered", "message": "Check your terminal for logs"}