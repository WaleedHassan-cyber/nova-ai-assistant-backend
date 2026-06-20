from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.db import connect_to_mongo, close_mongo_connection
from app.api.v1.endpoints import auth, chat, sync
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.user_router import router as user_api
from app.api.v1.endpoints.chat_session import router as sessions_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)


origins = [
    "http://localhost:59943",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- ROUTES ---
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/v1", tags=["AI"])
app.include_router(sync.router, prefix="/api/v1", tags=["Sync"]) # <--- 2. Register karein

app.include_router(user_api, prefix="/api/v1/user", tags=["User"])

app.include_router(sessions_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "NOVA Backend is running smoothly!"}