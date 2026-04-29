"""Task service — handles task creation, enqueueing, and execution.

For local development, uses background threads.
For production with USE_CLOUD_TASKS=true, uses Google Cloud Tasks.
"""
import os
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Dict, Any

from models import Task, FirestoreCollections

logger = logging.getLogger(__name__)

USE_CLOUD_TASKS = os.getenv("USE_CLOUD_TASKS", "false").lower() == "true"
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
LOCATION = os.getenv("CLOUD_TASKS_LOCATION", "us-central1")
QUEUE_NAME = os.getenv("CLOUD_TASKS_QUEUE", "bianca-task-queue")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TASKS_SERVICE_ACCOUNT = os.getenv("TASKS_SERVICE_ACCOUNT", "")

# Task executor registry — maps task_type to executor function
_EXECUTORS: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = {}

# Cloud Tasks client (lazy-initialized)
_cloud_tasks_client = None


def register_executor(task_type: str):
    """Decorator to register a task executor function."""
    def decorator(func: Callable[[str, Dict[str, Any]], Dict[str, Any]]):
        _EXECUTORS[task_type] = func
        logger.info(f"Registered executor for task type: {task_type}")
        return func
    return decorator


class TaskService:
    """Service for managing background tasks."""

    def __init__(self):
        self.fs = FirestoreCollections()

    def create_task(
        self,
        user_id: str,
        task_type: str,
        parameters: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Task:
        """Create a new task in Firestore."""
        task = Task(
            user_id=user_id,
            session_id=session_id,
            task_type=task_type,
            parameters=parameters,
            status="pending",
            progress=0,
            progress_message="Queued",
        )
        self.fs.create_task(task)
        logger.info(f"Created task {task.task_id} type={task_type} for user={user_id}")
        return task

    def enqueue(self, task_id: str) -> None:
        """Enqueue a task for execution."""
        if USE_CLOUD_TASKS:
            self._enqueue_cloud_tasks(task_id)
        else:
            self._enqueue_local(task_id)

    def _enqueue_local(self, task_id: str) -> None:
        """Execute task in a background thread (local dev mode)."""
        thread = threading.Thread(
            target=self._execute_task_sync,
            args=(task_id,),
            daemon=True,
        )
        thread.start()
        logger.info(f"Enqueued task {task_id} for local execution")

    def _enqueue_cloud_tasks(self, task_id: str) -> None:
        """Enqueue task to Google Cloud Tasks (production mode)."""
        global _cloud_tasks_client

        if not PROJECT_ID or not TASKS_SERVICE_ACCOUNT:
            logger.warning("Cloud Tasks not configured, falling back to local execution")
            self._enqueue_local(task_id)
            return

        try:
            # Lazy-initialize Cloud Tasks client
            if _cloud_tasks_client is None:
                from google.cloud import tasks_v2
                _cloud_tasks_client = tasks_v2.CloudTasksClient()

            parent = _cloud_tasks_client.queue_path(PROJECT_ID, LOCATION, QUEUE_NAME)

            task_payload = {
                "http_request": {
                    "http_method": "POST",
                    "url": f"{BACKEND_URL}/tasks/execute/{task_id}",
                    "oidc_token": {
                        "service_account_email": TASKS_SERVICE_ACCOUNT,
                    },
                }
            }

            response = _cloud_tasks_client.create_task(
                request={"parent": parent, "task": task_payload}
            )

            # Store Cloud Tasks name for tracking
            self.fs.update_task(task_id, cloud_task_name=response.name)
            logger.info(f"Enqueued task {task_id} to Cloud Tasks: {response.name}")

        except Exception as e:
            logger.error(f"Failed to enqueue to Cloud Tasks: {e}, falling back to local")
            self._enqueue_local(task_id)

    def _execute_task_sync(self, task_id: str) -> None:
        """Execute a task synchronously (called by background thread or Cloud Tasks)."""
        task = self.fs.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        if task.status != "pending":
            logger.warning(f"Task {task_id} is not pending (status={task.status})")
            return

        # Update status to running
        self.fs.update_task(
            task_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            progress=10,
            progress_message="Starting...",
        )

        executor = _EXECUTORS.get(task.task_type)
        if not executor:
            self.fs.update_task(
                task_id,
                status="failed",
                error=f"No executor registered for task type: {task.task_type}",
                completed_at=datetime.now(timezone.utc),
            )
            logger.error(f"No executor for task type: {task.task_type}")
            return

        try:
            result = executor(task.user_id, task.parameters)
            self.fs.update_task(
                task_id,
                status="completed",
                result=result,
                progress=100,
                progress_message="Completed",
                completed_at=datetime.now(timezone.utc),
            )
            logger.info(f"Task {task_id} completed successfully")

            # Task chaining — if the completed task carried a next_task spec,
            # build the follow-up task and enqueue it.  For document tasks the
            # result contains the Drive URL which is injected into the email body
            # so Gmail renders it as a native Drive file card.
            next_spec = task.parameters.get("next_task")
            if next_spec and isinstance(result, dict) and result.get("url"):
                next_params = next_spec.get("parameters", {}).copy()
                drive_url = result["url"]
                doc_title = result.get("title", result.get("name", "document"))
                next_params["body"] = (
                    next_params.get("body", "").rstrip()
                    + f"\n\n{doc_title}: {drive_url}"
                )
                follow_up = self.create_task(
                    task.user_id,
                    next_spec["type"],
                    next_params,
                    task.session_id,
                )
                self.enqueue(follow_up.task_id)
                logger.info(
                    "Chained task %s → %s (%s)",
                    task_id, follow_up.task_id, next_spec["type"],
                )
        except Exception as e:
            self.fs.update_task(
                task_id,
                status="failed",
                error=str(e),
                progress_message="Failed",
                completed_at=datetime.now(timezone.utc),
            )
            logger.error(f"Task {task_id} failed: {e}")

    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a task (called by Cloud Tasks callback endpoint)."""
        self._execute_task_sync(task_id)
        task = self.fs.get_task(task_id)
        return task.model_dump() if task else {"error": "Task not found"}

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.fs.get_task(task_id)

    def list_tasks(
        self, user_id: str, status: Optional[str] = None, limit: int = 50
    ) -> list[Task]:
        """List tasks for a user."""
        return self.fs.list_tasks(user_id, status, limit)

    def cancel_task(self, task_id: str, user_id: str) -> bool:
        """Cancel a pending task. Returns True if cancelled."""
        task = self.fs.get_task(task_id)
        if not task:
            return False
        if task.user_id != user_id:
            return False
        if task.status != "pending":
            return False

        self.fs.update_task(
            task_id,
            status="failed",
            error="Cancelled by user",
            completed_at=datetime.now(timezone.utc),
        )
        return True

    def delete_task(self, task_id: str, user_id: str) -> bool:
        """Delete a task. Only completed/failed tasks can be deleted."""
        task = self.fs.get_task(task_id)
        if not task:
            return False
        if task.user_id != user_id:
            return False
        if task.status in ("pending", "running"):
            return False

        return self.fs.delete_task(task_id)

    def retry_task(self, task_id: str, user_id: str) -> Optional[Task]:
        """Retry a failed task. Resets it to pending and re-enqueues."""
        task = self.fs.get_task(task_id)
        if not task:
            return None
        if task.user_id != user_id:
            return None
        if task.status != "failed":
            return None

        self.fs.update_task(
            task_id,
            status="pending",
            progress=0,
            progress_message="Queued (retry)",
            error=None,
            started_at=None,
            completed_at=None,
            result=None,
        )
        self.enqueue(task_id)
        logger.info(f"Retried task {task_id}")
        return self.fs.get_task(task_id)


# Singleton instance
task_service = TaskService()


# ── Register built-in executors ─────────────────────────────────────────────


@register_executor("create_document")
def execute_create_document(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a formatted binary document (docx/xlsx/pptx/pdf) from LLM-generated
    code and upload it to Google Drive.

    Expected params:
        document_type : "docx" | "xlsx" | "pptx" | "pdf"
        title         : human-readable document title (used as filename)
        code          : complete generation code (JS for docx/pptx, Python for xlsx/pdf)
    """
    from tools.document_engine import execute_and_upload

    document_type = params.get("document_type", "docx")
    title = params.get("title", "Untitled Document")
    code = params.get("code", "")
    return execute_and_upload(user_id, document_type, title, code)


@register_executor("generate_and_create_document")
def execute_generate_and_create_document(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full pipeline: call LLM to generate document code from the user's request,
    then execute and upload to Google Drive.

    Expected params:
        user_message  : original user request text
        document_type : "docx" | "xlsx" | "pptx" | "pdf"
        title         : pre-extracted title hint
        model         : LLM model to use for code generation
        anthropic_api_key : optional Anthropic key override
    """
    import re
    from document_skill_loader import _load_instructions
    from tools.document_engine import execute_and_upload
    from settings_loader import load_settings

    user_message = params.get("user_message", "")
    document_type = params.get("document_type", "docx")
    title = params.get("title", "Document")

    settings = load_settings()
    model = params.get("model") or settings.get("model", "claude-sonnet-4-6")
    api_key = (
        params.get("anthropic_api_key", "").strip()
        or settings.get("anthropic_api_key", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "")
    )

    instructions = _load_instructions(document_type)
    format_names = {
        "docx": "Word document (.docx)",
        "xlsx": "Excel spreadsheet (.xlsx)",
        "pptx": "PowerPoint presentation (.pptx)",
        "pdf": "PDF document (.pdf)",
    }
    code_libs = {
        "docx": "docx-js (Node.js — require('docx'))",
        "xlsx": "openpyxl (Python)",
        "pptx": "pptxgenjs (Node.js — require('pptxgenjs'))",
        "pdf": "reportlab (Python)",
    }

    prompt = f"""You are a code generator. The user wants to create a {format_names[document_type]}.

User request:
{user_message}

--- GENERATION INSTRUCTIONS ---
{instructions}

Generate COMPLETE, runnable {code_libs[document_type]} code that fulfils the user's request.
Rules:
- Return ONLY the raw code, no markdown fences, no explanation
- First line must be: # TITLE: <a good filename for this document>
- The code must write the output file to the current working directory
- Follow all critical rules from the instructions above exactly"""

    # Call the LLM (Anthropic or Vertex AI)
    if model.startswith("claude"):
        import anthropic
        if not api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY in backend/.env")
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=8096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
    else:
        from langchain_google_vertexai import ChatVertexAI
        from config import GCP_PROJECT_ID, GCP_LOCATION
        llm = ChatVertexAI(model=model, project=GCP_PROJECT_ID, location=GCP_LOCATION, temperature=0.3)
        raw = llm.invoke(prompt).content

    # Strip markdown fences if the model added them despite instructions
    code = re.sub(r'^```[\w]*\n?', '', raw, flags=re.MULTILINE)
    code = re.sub(r'^```\n?', '', code, flags=re.MULTILINE)
    code = code.strip()

    # Extract TITLE comment if present
    lines = code.splitlines()
    if lines and lines[0].startswith("# TITLE:"):
        extracted = lines[0].replace("# TITLE:", "").strip()
        if extracted:
            title = extracted
        code = "\n".join(lines[1:]).strip()

    logger.info("Generated %s code (%d chars) for '%s'", document_type, len(code), title)
    return execute_and_upload(user_id, document_type, title, code)


@register_executor("send_email")
def execute_send_email(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send an email."""
    from tools.gmail import send_email

    to = params["to"]
    subject = params["subject"]
    body = params["body"]
    result = send_email(user_id, to, subject, body)
    return result


@register_executor("draft_email")
def execute_draft_email(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create an email draft."""
    from tools.gmail import draft_email

    to = params["to"]
    subject = params["subject"]
    body = params["body"]
    result = draft_email(user_id, to, subject, body)
    return result
