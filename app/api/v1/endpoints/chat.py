from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.core.db import db_connection
from app.services.ai_service import get_nova_response, get_nova_structured_chat
from app.services.memory_service import get_user_memory, update_user_memory
from app.schemas.chat import ChatRequest

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    user_id = request.user_id
    user_msg = request.message
    db = db_connection.db

    db_context = ""
    # Purana context fetch logic yahan aa jaye ga
    if any(word in user_msg.lower() for word in ["list", "reminder", "kaam", "todo", "hata", "delete", "batao"]):
        pass

    #FETCH CHAT HISTORY
    history = await get_user_memory(user_id)

    #SMART ROUTING
    # Agar user document/email mang raha hai
    document_keywords = ["email", "letter", "application", "draft", "khat", "likho", "write an email"]

    if any(word in user_msg.lower() for word in document_keywords) and not any(
            word in user_msg.lower() for word in ["reminder", "todo", "call", "open"]):
        # Call structured chat function
        ai_response = await get_nova_structured_chat(user_msg, history)

        # Structured chats ko hmsha mmry me save krty hai
        await update_user_memory(user_id, "user", user_msg)
        # Email draft ka main reply ya subject memory mein daal dete hain context ke liye
        await update_user_memory(user_id, "model", ai_response.get("reply", "Draft generated."))

        return ai_response

    #STANDARD AI RESPONSE
    ai_response = await get_nova_response(user_msg + db_context, history)
    action_type = ai_response.get("action")

    #ACTION HANDLING (Writing/Deleting to MongoDB)

    #REMINDERS
    if action_type == "reminder_add":
        await db.reminders.insert_one({
            "user_id": user_id,
            "title": ai_response.get("task"),
            "remind_at": datetime.fromisoformat(ai_response.get("time").replace('Z', '')),
            "is_notified": False,
            "status": "pending",
            "created_at": datetime.utcnow()
        })
    elif action_type == "reminder_delete":
        await db.reminders.delete_many({
            "user_id": user_id,
            "title": {"$regex": ai_response.get("keyword"), "$options": "i"}
        })

    #TO-DOS (use me ni but still code ha)
    elif action_type == "todo_add":
        items = ai_response.get("item").split(",")
        for item in items:
            await db.todos.insert_one({
                "user_id": user_id,
                "item": item.strip(),
                "status": "pending",
                "created_at": datetime.utcnow()
            })
    elif action_type == "todo_delete":
        await db.todos.delete_many({
            "user_id": user_id,
            "item": {"$regex": ai_response.get("keyword"), "$options": "i"}
        })

    #MEMORY UPDATE
    save_actions = ["reminder_add", "reminder_delete", "todo_add", "todo_delete"]

    if ai_response.get("type") == "chat" or action_type in save_actions:
        await update_user_memory(user_id, "user", user_msg)
        await update_user_memory(user_id, "model", ai_response.get("reply", ""))

    return ai_response