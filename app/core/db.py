from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class DatabaseConnection:
    client: AsyncIOMotorClient = None
    db = None

db_connection = DatabaseConnection()

async def connect_to_mongo():
    # 1. MongoDB Client Initialize karein
    db_connection.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db_connection.db = db_connection.client[settings.DATABASE_NAME]

    # --- UPDATED INDEXING LOGIC (Single Collection Strategy) ---

    # A. TASKS COLLECTION INDEXES
    # 1. Sync Index: user_id aur task_id ka combination unique hona chahiye.
    # Is se Upsert (Update or Insert) ki speed 100x fast ho jati hai.
    await db_connection.db.tasks.create_index(
        [("user_id", 1), ("id", 1)],
        unique=True,
        name="user_task_sync_idx"
    )

    # 2. Query Index: Jab hum sirf reminders ya sirf todos filter karenge.
    # Is se status update aur remind_at search fast hogi.
    await db_connection.db.tasks.create_index(
        [("user_id", 1), ("type", 1), ("status", 1)],
        name="user_task_filter_idx"
    )

    # 3. Reminder Timing Index: Future reminders fetch karne ke liye.
    await db_connection.db.tasks.create_index(
        [("remind_at", 1)],
        name="task_reminder_time_idx",
        sparse=True  # Sirf un documents ke liye jin mein remind_at field ho
    )

    # B. CONVERSATIONS INDEX
    # User_id ko unique rakha hai taaki chat history mix na ho.
    await db_connection.db.conversations.create_index(
        "user_id",
        unique=True,
        name="unique_user_chat_idx"
    )

    await db_connection.db.chat_sessions.create_index(
        [("user_id", 1), ("messages", 1), ("last_message_at", -1)],
        name="user_session_lookup_idx"
    )

    # 2. Session ID lookup (Optional but recommended for fetching specific chat)
    await db_connection.db.chat_sessions.create_index(
        "session_id",
        unique=True,
        name="unique_session_id_idx"
    )

    print("✅ Database connected successfully!")
    print("🚀 All Single-Collection Indexes (Tasks & Conversations) are active.")

async def close_mongo_connection():
    if db_connection.client:
        db_connection.client.close()
        print("🛑 MongoDB connection closed.")