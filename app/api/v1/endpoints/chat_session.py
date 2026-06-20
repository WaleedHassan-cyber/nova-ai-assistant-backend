import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Body, status
from app.core.db import db_connection
from app.schemas.chat_session import (
    ChatRequest,
    ChatSession,
    ChatMessage,
    NewSessionResponse,
    SessionSummary,
    SessionMessagesResponse,
)
from app.services.ai_service import get_nova_response, get_nova_structured_chat

router = APIRouter(prefix="/sessions", tags=["Chat Sessions"])


# Session fetch helper
async def _get_session_or_404(db, session_id: str, user_id: str) -> dict:
    session = await db.chat_sessions.find_one(
        {"session_id": session_id, "user_id": user_id}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# POST /sessions/new ---> naya session
@router.post("/new", response_model=NewSessionResponse)
async def create_session(user_id: str = Body(..., embed=True)):
    db = db_connection.db

    # Pehle check karein ke kya koi aisa session hai jisme messages empty hain []
    # Humne index "user_session_lookup_idx" isi liye banaya tha
    existing_empty_session = await db.chat_sessions.find_one({
        "user_id": user_id,
        "messages": []
    })

    #Agar khali session mil jaye, to naya banane ki bajaye wahi return kar dein
    if existing_empty_session:
        return NewSessionResponse(
            session_id=existing_empty_session["session_id"],
            created_at=existing_empty_session["created_at"]
        )

    #Agar koi khali session nahi mila, tabhi naya session create karein
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()

    new_session = {
        "session_id": session_id,
        "user_id": user_id,
        "preview": "New conversation",
        "messages": [],
        "created_at": now,
        "last_message_at": now,
    }

    await db.chat_sessions.insert_one(new_session)
    return NewSessionResponse(session_id=session_id, created_at=now)


# GET /sessions/{user_id} ---> user ky sari sessions
@router.get("/{user_id}", response_model=list[SessionSummary])
async def get_sessions(user_id: str):
    db = db_connection.db

    cursor = db.chat_sessions.find(
        {"user_id": user_id},
        {"messages": 0}  # messages field nahi chahiye sidebar ke liye
    ).sort("last_message_at", -1).limit(50)

    sessions = await cursor.to_list(length=50)

    return [
        SessionSummary(
            session_id=s["session_id"],
            preview=s.get("preview", "New conversation"),
            created_at=s["created_at"],
            last_message_at=s["last_message_at"],
        )
        for s in sessions
    ]


# GET /sessions/{user_id}/{session_id} ----> ek session ke messages
@router.get("/{user_id}/{session_id}", response_model=SessionMessagesResponse)
async def get_session_messages(user_id: str, session_id: str):
    db = db_connection.db
    session = await _get_session_or_404(db, session_id, user_id)

    messages = [
        ChatMessage(
            role=m["role"],
            parts=m["parts"],
            type=m.get("type", "chat"),
            timestamp=m.get("timestamp", datetime.utcnow()),
            email_subject=m.get("email_subject"),
            email_body=m.get("email_body"),
        )
        for m in session.get("messages", [])
    ]

    return {"session_id": session_id, "messages": messages}


# POST /sessions/chat ---->  message bhejo, AI reply lo, DB update karo
@router.post("/chat")
async def chat(request: ChatRequest):
    db = db_connection.db
    user_id = request.user_id
    user_msg = request.message
    session_id = request.session_id
    now = datetime.utcnow()

    is_new_session = False

    if not session_id or session_id.strip() == "":
        existing_empty_session = await db.chat_sessions.find_one({
            "user_id": user_id,
            "messages": []
        })

        if existing_empty_session:
            # Agar khali session mil gaya, to uski ID reuse karo
            session_id = existing_empty_session["session_id"]
        else:
            # Agar koi khali session nahi mila, tabhi bilkul naya banao
            session_id = str(uuid.uuid4())
            is_new_session = True
            await db.chat_sessions.insert_one({
                "session_id": session_id,
                "user_id": user_id,
                "preview": user_msg[:40],
                "messages": [],
                "created_at": now,
                "last_message_at": now,
            })
    else:
        # ✅ Frontend se session_id aayi hai — check karo ke wo DB mein exist karti hai ya nahi
        existing_session = await db.chat_sessions.find_one(
            {"session_id": session_id, "user_id": user_id}
        )
        if not existing_session:
            # Stale/invalid session_id thi (delete ho gayi ya kabhi bani hi nahi)
            # 404 dene ke bajaye, isi id ke sath naya session bana do
            is_new_session = True
            await db.chat_sessions.insert_one({
                "session_id": session_id,
                "user_id": user_id,
                "preview": user_msg[:40],
                "messages": [],
                "created_at": now,
                "last_message_at": now,
            })

    # ── 2. History fetch karo ────────────────────────────────────
    if is_new_session:
        history = []
    else:
        session = await _get_session_or_404(db, session_id, user_id)
        history = session.get("messages", [])

    # ── 3. History ko AI format mein convert karo ──────────────────
    chat_history = [
        {"role": m["role"], "parts": [m["parts"]]} for m in history
    ]

    # ── 4. Smart routing: email/draft ya normal ───────────────────
    document_keywords = ["email", "letter", "application", "draft", "khat", "likho"]
    skip_keywords = ["reminder", "todo", "call", "open"]

    is_document = any(w in user_msg.lower() for w in document_keywords) and not any(
        w in user_msg.lower() for w in skip_keywords
    )

    if is_document:
        ai_response = await get_nova_structured_chat(
            user_text=user_msg,
            chat_history=chat_history,
        )
    else:
        ai_response = await get_nova_response(
            user_text=user_msg,
            chat_history=chat_history,
        )

    reply_text = ai_response.get("reply", "")
    msg_type = ai_response.get("type", "chat")
    action_type = ai_response.get("action")

    # ── 5. ACTION HANDLING (Reminders / Todos Sync) ────────────────
    if action_type == "reminder_add":
        time_str = ai_response.get("time", "").replace('Z', '+00:00')
        try:
            remind_dt = datetime.fromisoformat(time_str)
        except ValueError:
            remind_dt = now

        await db.reminders.insert_one({
            "user_id": user_id,
            "title": ai_response.get("task"),
            "remind_at": remind_dt,
            "is_notified": False,
            "status": "pending",
            "created_at": now
        })
    elif action_type == "reminder_delete":
        await db.reminders.delete_many({
            "user_id": user_id,
            "title": {"$regex": ai_response.get("keyword", ""), "$options": "i"}
        })
    elif action_type == "todo_add":
        items = ai_response.get("item", "").split(",")
        for item in items:
            if item.strip():
                await db.todos.insert_one({
                    "user_id": user_id,
                    "item": item.strip(),
                    "status": "pending",
                    "created_at": now
                })
    elif action_type == "todo_delete":
        await db.todos.delete_many({
            "user_id": user_id,
            "item": {"$regex": ai_response.get("keyword", ""), "$options": "i"}
        })

    # ── 6. Dono Messages (User + Model) DB mein save karo ──────────
    user_msg_doc = {
        "role": "user",
        "parts": user_msg,
        "type": "chat",
        "timestamp": now,
    }

    model_msg_doc = {
        "role": "model",
        "parts": reply_text,
        "type": msg_type,
        "timestamp": datetime.utcnow(),
        "email_subject": ai_response.get("subject") if msg_type == "document_draft" else None,
        "email_body": ai_response.get("body") if msg_type == "document_draft" else None,
    }

    # Ab chahe naya bana ho ya purana reuse hua ho, dono cases me messages array push ho jayega
    await db.chat_sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": {"$each": [user_msg_doc, model_msg_doc]}},
            "$set": {
                "preview": user_msg[:40],
                "last_message_at": datetime.utcnow(),
            },
        },
    )

    # ── 7. Response return karo Flutter ko ─────────────────────────
    return {
        **ai_response,
        "session_id": session_id,
    }


# ─────────────────────────────────────────────────────────────────
# DELETE /sessions/{user_id}/{session_id}  →  Session delete karo
# ─────────────────────────────────────────────────────────────────
@router.delete("/{user_id}/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(user_id: str, session_id: str):
    db = db_connection.db

    # Session ko delete karne ki koshish karein
    result = await db.chat_sessions.delete_one({
        "session_id": session_id,
        "user_id": user_id
    })

    # Agar koi document delete nahi hua (matlab session_id galat hai ya user uska owner nahi hai)
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Session nahi mila ya aap ise delete nahi kar sakte"
        )

    return {"message": "Session successfully delete ho gaya", "session_id": session_id}