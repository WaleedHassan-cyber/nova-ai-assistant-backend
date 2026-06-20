from app.core.db import db_connection
from app.core.firebase import send_push_notification
from datetime import datetime
from bson import ObjectId


async def check_reminders():
    db = db_connection.db
    current_time = datetime.utcnow()

    print(f"Checking reminders at: {current_time}")

    query = {
        "is_notified": False,
        "remind_at": {"$lte": current_time}
    }

    pending_reminders = await db.reminders.find(query).to_list(100)
    print(f"Found {len(pending_reminders)} pending reminders")

    for reminder in pending_reminders:
        # FIX: Agar user_id string hai toh usay ObjectId mein convert karna zaroori hai
        u_id = reminder["user_id"]
        try:
            target_id = ObjectId(u_id) if isinstance(u_id, str) else u_id
            user = await db.users.find_one({"_id": target_id})
        except Exception as e:
            print(f"Error parsing user_id: {e}")
            continue

        if user and user.get("fcm_token"):
            print(f"Sending notification to user: {user.get('email')}")
            success = send_push_notification(
                token=user["fcm_token"],
                title="NOVA Task Alert 🔔",
                body=reminder["title"]
            )

            if success:
                await db.reminders.update_one(
                    {"_id": reminder["_id"]},
                    {"$set": {"is_notified": True, "status": "completed"}}
                )
                print(f"Reminder {reminder['_id']} marked as completed.")
        else:
            # Ye tab print hoga agar user nahi mila ya uska FCM token DB mein nahi hai
            print(f"Skipping: No FCM token found for user_id: {u_id}")