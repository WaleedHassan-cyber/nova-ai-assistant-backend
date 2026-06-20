from datetime import datetime
from app.core.db import db_connection

async def update_user_memory(user_id: str, role: str, message: str):
    """Memory update karne ka logic - Now in its correct service layer"""
    if db_connection.db is None:
        return

    new_message = {
        "role": role,
        "parts": message,
        "timestamp": datetime.utcnow()
    }

    await db_connection.db.conversations.update_one(
        {"user_id": user_id},
        {
            "$push": {
                "messages": {
                    "$each": [new_message],
                    "$slice": -10
                }
            },
            "$set": {"last_updated": datetime.utcnow()}
        },
        upsert=True
    )

async def get_user_memory(user_id: str):
    """Memory fetch karne ka logic"""
    if db_connection.db is None:
        return []

    doc = await db_connection.db.conversations.find_one({"user_id": user_id})
    if doc and "messages" in doc:
        return [{"role": m["role"], "parts": [m["parts"]]} for m in doc["messages"]]
    return []