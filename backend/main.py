"""FastAPI entry point for the AI Chief of Staff backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.chat import router as chat_router
from routers.admin import router as admin_router
from routers.voice import router as voice_router
from routers.auth import router as auth_router
from routers.skills import router as skills_router
from routers.config import router as config_router

app = FastAPI(title="AI Chief of Staff", version="0.3.0")

# Add CORS middleware for frontend integration (Phase 4A: includes SSE support)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Cache-Control"],  # Needed for SSE
)

app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(voice_router)
app.include_router(auth_router)
app.include_router(skills_router)
app.include_router(config_router)


@app.get("/")
def health():
    return {"status": "ok", "version": "0.4.0", "phase": "4A - Streaming"}
