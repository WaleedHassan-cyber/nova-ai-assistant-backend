import datetime
import random
from bson import ObjectId
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.config import settings
from app.core.db import db_connection
from app.services.auth_services import hash_password, create_access_token, verify_password
from fastapi import APIRouter, HTTPException, Body
from app.utils.email_utils import send_otp_email

router = APIRouter()


@router.post("/register")
async def register(
    email: str = Body(...),
    username: str = Body(...),
    password: str = Body(...),
    fcm_token: str = Body(None)
):
    db = db_connection.db
    existing_user = await db.users.find_one({"$or": [{"email": email}, {"username": username}]})
    if existing_user:
        raise HTTPException(status_code=422, detail="User already exists")

    otp = str(random.randint(100000, 999999))
    otp_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)

    # 🔥 FIX: Password ko YAHA hi hash kar dein
    hashed_password = hash_password(password)

    new_user = {
        "email": email,
        "username": username,
        "password": hashed_password, # Ab DB mein asli password kabhi nahi jayega
        "provider": "email",
        "otp": otp,
        "otp_expiry": otp_expiry,
        "is_verified": False,
        "fcm_token": fcm_token,
        "log_alerts": False,
        "is2FAEnabled": False,
        "profile_pic_url": None
    }

    await db.users.insert_one(new_user)

    try:
        await send_otp_email(email, otp)
    except Exception as e:
        print(f"--- FALLBACK DEBUG OTP: {otp} ---")

    return {"message": "OTP sent successfully", "email": email}


@router.post("/verify-otp")
async def verify_otp(email: str = Body(...), otp: str = Body(...)):
    db = db_connection.db

    # 1. User dhoondo
    user = await db.users.find_one({"email": email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Expiry check karein (Null check ke saath)
    expiry = user.get("otp_expiry")

    if expiry is None:
        # Iska matlab ya toh OTP verify ho chuka hai ya kabhi generate hi nahi hua
        raise HTTPException(
            status_code=422,
            detail="No active OTP request found or email already verified"
        )

    #Ensure time in Utc
    current_time = datetime.datetime.now(datetime.timezone.utc)

    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=datetime.timezone.utc)

    #OTP & Expiry Match
    db_otp = user.get("otp")

    if db_otp != otp:
        raise HTTPException(status_code=422, detail="Invalid OTP code")

    if expiry < current_time:
        raise HTTPException(status_code=422, detail="OTP has expired. Please register again")

    #Success
    await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "is_verified": True,
                "otp": None,
                "otp_expiry": None
            }
        }
    )

    #Token generate
    token = create_access_token(str(user["_id"]))
    return {
        "status": "success",
        "token": token,
        "user_id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "profile_pic_url": user.get("profile_pic_url"),
        "log_alerts": user.get("log_alerts"),
        "is2FAEnabled": user.get("is2FAEnabled"),
    }

@router.post("/login")
async def login(
        email: str = Body(None),
        password: str = Body(None),
        provider: str = Body(...),  # email or google
        idToken: str = Body(None),
        fcm_token: str = Body(None)
):
    db = db_connection.db
    # GOOGLE LOGIN
    # print(idToken)
    if provider == "google":
        if not idToken:
            print("[DEBUG LOGIN] Google idToken missing in request")
            raise HTTPException(status_code=400, detail="Google idToken is required")
        try:
            print(f"[DEBUG LOGIN] Verifying Google idToken: {idToken[:20]}...")
            id_info = id_token.verify_oauth2_token(
                idToken,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            #verification Passed
            print(f"[DEBUG LOGIN] Verification Passed for: {id_info.get('email')}")
            google_email = id_info['email']
            google_id = id_info['sub']
            google_name = id_info.get('name')
            google_picture = id_info.get('picture')

            user = await db.users.find_one({"email": google_email})
            if user and user.get("provider") == "email":
                print(f"[DEBUG LOGIN] User {google_email} exists with manual 'email' provider")
                raise HTTPException(status_code=400, detail="Use manual login for this account")
            if not user:
                print(f"[DEBUG LOGIN] User not found. Auto-registering Google User: {google_email}")
                # Auto-register Google User
                new_user = {
                    "email": google_email,
                    "username": google_name,
                    "provider": "google",
                    "google_id": google_id,
                    "is_verified": True,
                    "profile_pic_url": google_picture,
                    "log_alerts": False,
                    "is2FAEnabled": False,
                }
                result = await db.users.insert_one(new_user)
                user = new_user
                user["_id"] = result.inserted_id
                print(f"[DEBUG LOGIN] New Google user registered with ID: {user['_id']}")
            else:
                print(f"[DEBUG LOGIN] Google user found in DB: {user['_id']}")
                if fcm_token:
                    await db.users.update_one({"_id": user["_id"]}, {"$set": {"fcm_token": fcm_token}})
            user_id = str(user["_id"])
            token = create_access_token(user_id)
            print(f"[DEBUG LOGIN] Token created successfully for user_id: {user_id}")
            return {
                "status": "success",
                "token": token,
                "user_id": user_id,
                "username": user["username"],
                "email": user["email"],
                "profile_pic_url": user.get("profile_pic_url"),
                "log_alerts": user.get("log_alerts", False),
                "is2FAEnabled": user.get("is2FAEnabled", False),
            }
        except HTTPException as he:
            print(f"[DEBUG LOGIN] HTTP Exception caught: {he.detail}")
            raise he
        except Exception as e:
            import traceback
            print(f"[DEBUG LOGIN] Exception during Google Auth: {str(e)}")
            print(traceback.format_exc())
            raise HTTPException(status_code=401, detail="Invalid Google Token")
    #MANUAL LOGIN
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.get("is_verified"):
        raise HTTPException(status_code=401, detail="Please verify your email first")
    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if fcm_token:
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"fcm_token": fcm_token}})
    token = create_access_token(str(user["_id"]))
    return {
        "status": "success",
        "token": token,
        "user_id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "profile_pic_url": user.get("profile_pic_url"),
        "log_alerts": user.get("log_alerts", False),
        "is2FAEnabled": user.get("is2FAEnabled", False),
    }

@router.post("/resend-otp")
async def resend_otp(
    email: str = Body(...),
):
    db = db_connection.db

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("provider") == "google":
        raise HTTPException(status_code=400, detail="Google accounts do not require OTP verification")

    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Account is already verified")

    current_time = datetime.datetime.now(datetime.timezone.utc)
    existing_expiry = user.get("otp_expiry")

    # ── KEY LOGIC ──────────────────────────────────────────
    # Agar expiry exist karti hai aur abhi bhi 2.5 min bacha hai
    # toh naya OTP generate nhi ho ga
    if existing_expiry:
        if existing_expiry.tzinfo is None:
            existing_expiry = existing_expiry.replace(tzinfo=datetime.timezone.utc)

        remaining_seconds = (existing_expiry - current_time).total_seconds()

        if remaining_seconds > 150:  #150 sec = 2.5 min
            return {
                "status": "existing",
                "message": "OTP already sent and still valid",
                "email": email,
                "remaining_seconds": int(remaining_seconds),
            }
    # Otherwise
    new_otp = str(random.randint(100000, 999999))
    new_expiry = current_time + datetime.timedelta(minutes=5)

    await db.users.update_one(
        {"email": email},
        {"$set": {"otp": new_otp, "otp_expiry": new_expiry}}
    )

    try:
        await send_otp_email(email, new_otp)
    except Exception as e:
        print(f"--- FALLBACK DEBUG OTP (resend): {new_otp} ---")

    return {
        "status": "success",
        "message": "New OTP sent successfully",
        "email": email,
        "remaining_seconds": 300,
    }
# @router.post("/refresh-fcm-token")
# async def refresh_fcm_token(
#         user_id: str = Body(...),
#         token: str = Body(...)
# ):
#     db = db_connection.db
#
#     # Chek user object is valid or not
#     if not ObjectId.is_valid(user_id):
#         raise HTTPException(status_code=400, detail="Invalid User ID")
#
#     # Update new token
#     result = await db.users.update_one(
#         {"_id": ObjectId(user_id)},
#         {"$set": {"fcm_token": token}}
#     )
#
#     if result.matched_count == 0:
#         raise HTTPException(status_code=404, detail="User not found")
#
#     return {"status": "success", "message": "FCM token updated successfully"}

@router.patch("/update-settings")
async def update_settings(
    body: dict = Body(...)
):
    db = db_connection.db
    user_id = body.get("userId")

    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid User ID")

    update_data = {k: v for k, v in body.items() if k != "userId"}

    if not update_data:
        raise HTTPException(status_code=422, detail="No settings provided to update")

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "success", "message": "Setting updated successfully"}


@router.post("/change-password")
async def change_password(
    email: str = Body(...),
    old_password: str = Body(...),
    new_password: str = Body(...)
):
    db = db_connection.db

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("provider") == "google":
        raise HTTPException(
            status_code=400,
            detail="Google accounts do not have a password. Please use Google sign-in"
        )

    if not verify_password(old_password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect old password")

    hashed_new_password = hash_password(new_password)

    await db.users.update_one(
        {"email": email},
        {"$set": {"password": hashed_new_password}}
    )

    return {"status": "success", "message": "Password updated successfully"}