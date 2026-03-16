"""Tasks router — CRUD and execution endpoints for background tasks."""
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from task_service import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── Request/Response Models ─────────────────────────────────────────────────


class CreateTaskRequest(BaseModel):
    user_id: str
    task_type: str
    parameters: dict[str, Any]
    session_id: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    user_id: str
    session_id: Optional[str]
    task_type: str
    parameters: dict[str, Any]
    status: str
    progress: int
    progress_message: str
    result: Optional[dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


# ── CRUD Endpoints ──────────────────────────────────────────────────────────


@router.post("/", response_model=TaskResponse)
def create_task(request: CreateTaskRequest):
    """Create a new task and enqueue it for execution."""
    task = task_service.create_task(
        user_id=request.user_id,
        task_type=request.task_type,
        parameters=request.parameters,
        session_id=request.session_id,
    )
    task_service.enqueue(task.task_id)
    return TaskResponse(**task.model_dump())


@router.get("/", response_model=list[TaskResponse])
def list_tasks(user_id: str, status: Optional[str] = None, limit: int = 50):
    """List tasks for a user, optionally filtered by status."""
    tasks = task_service.list_tasks(user_id, status, limit)
    return [TaskResponse(**t.model_dump()) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, user_id: str):
    """Get details of a specific task."""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return TaskResponse(**task.model_dump())


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, user_id: str):
    """Cancel a pending task."""
    success = task_service.cancel_task(task_id, user_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel task (not found, not owned, or not pending)"
        )
    return {"ok": True, "message": "Task cancelled"}


@router.delete("/{task_id}")
def delete_task(task_id: str, user_id: str):
    """Delete a completed or failed task."""
    success = task_service.delete_task(task_id, user_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete task (not found, not owned, or still running)"
        )
    return {"ok": True, "message": "Task deleted"}


# ── Execution Endpoint (for Cloud Tasks callback) ───────────────────────────


@router.post("/execute/{task_id}")
async def execute_task(task_id: str, request: Request):
    """
    Cloud Tasks calls this endpoint to execute a task.
    In production, this validates the OIDC token from Cloud Tasks.
    In development, it executes directly.
    """
    # TODO: In production, validate OIDC token from Cloud Tasks
    # For now, execute directly
    result = task_service.execute_task(task_id)
    return result


# ── Health Check ────────────────────────────────────────────────────────────


@router.get("/health")
def tasks_health():
    """Health check for tasks service."""
    return {"status": "ok", "service": "tasks"}
