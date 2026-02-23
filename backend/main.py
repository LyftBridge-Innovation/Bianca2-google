"""FastAPI entry point for the AI Chief of Staff backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.tools_test import router as tools_test_router
from routers.chat import router as chat_router
from routers.admin import router as admin_router

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

app.include_router(tools_test_router)
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/")
def health():
    return {"status": "ok", "version": "0.4.0", "phase": "4A - Streaming"}
