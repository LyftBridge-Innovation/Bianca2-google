"""Tasks router — CRUD and execution endpoints for background tasks."""
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from task_service import task_service
from models import FirestoreCollections

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


# ── Real-time Updates (SSE) ─────────────────────────────────────────────────


@router.get("/stream")
async def stream_tasks(user_id: str):
    """
    Server-Sent Events endpoint for real-time task updates.
    Streams task changes for a specific user using Firestore listeners.
    """
    async def event_generator():
        """Generate SSE events from Firestore changes."""
        fs = FirestoreCollections()
        queue = asyncio.Queue()

        def on_snapshot(col_snapshot, changes, read_time):
            """Callback for Firestore real-time updates."""
            for change in changes:
                if change.type.name in ('ADDED', 'MODIFIED'):
                    task_data = change.document.to_dict()
                    # Only send if it belongs to this user
                    if task_data.get('user_id') == user_id:
                        asyncio.create_task(queue.put(task_data))

        # Subscribe to user's tasks
        query = fs.db.collection('tasks').where('user_id', '==', user_id)
        watch = query.on_snapshot(on_snapshot)

        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"

            # Stream updates
            while True:
                task_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(task_data, default=str)}\n\n"

        except asyncio.TimeoutError:
            # Send keepalive every 30 seconds
            yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Unsubscribe when client disconnects
            watch.unsubscribe()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# ── Health Check ────────────────────────────────────────────────────────────


@router.get("/health")
def tasks_health():
    """Health check for tasks service."""
    return {"status": "ok", "service": "tasks"}
