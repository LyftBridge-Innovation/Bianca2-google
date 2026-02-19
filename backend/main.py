"""FastAPI entry point for the AI Chief of Staff backend."""
from fastapi import FastAPI
from routers.tools_test import router as tools_test_router

app = FastAPI(title="AI Chief of Staff", version="0.1.0")

app.include_router(tools_test_router)


@app.get("/")
def health():
    return {"status": "ok"}
