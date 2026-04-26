# Background Task Queue Architecture

## Overview

Long-running operations (creating Google Docs, sending emails, generating presentations) should execute asynchronously to provide immediate user feedback. This document describes the architecture for a task queue system that:

1. Responds to users immediately instead of blocking
2. Persists tasks with user_id and all execution data
3. Executes tasks server-side with proper error handling
4. Supports multiple users with concurrent tasks
5. Provides a monitoring UI in Neural Config
6. Scales well when deployed to Google Cloud

---

## Architecture Decision: Google Cloud Tasks + Firestore

### Why Cloud Tasks?

| Option | Pros | Cons |
|--------|------|------|
| **FastAPI BackgroundTasks** | Simple, no infra | Lost on restart, no retry, single-server |
| **Celery + Redis** | Mature, powerful | Extra infrastructure, Redis cost |
| **Google Cloud Tasks** | Managed, durable, auto-retry, scales | GCP-specific |
| **Pub/Sub + Cloud Run** | Flexible, event-driven | More complex setup |

**Chosen: Cloud Tasks** because:
- Already using GCP (Firestore, Vertex AI)
- Durable queue (survives restarts)
- Built-in retry with exponential backoff
- HTTP target works directly with Cloud Run
- No additional infrastructure to manage
- Cost-effective for low-to-medium volume

---

## Data Model

### Firestore Collection: `tasks`

```python
class Task(BaseModel):
    task_id: str                    # UUID, primary key
    user_id: str                    # Owner of the task
    session_id: Optional[str]       # Chat session that created it

    # Task definition
    task_type: str                  # "create_doc", "send_email", "create_slides", etc.
    parameters: dict[str, Any]      # All inputs needed to execute

    # Status tracking
    status: str                     # "pending", "running", "completed", "failed"
    progress: int                   # 0-100 percentage
    progress_message: str           # Human-readable status

    # Results
    result: Optional[dict]          # Output data (doc URL, email ID, etc.)
    error: Optional[str]            # Error message if failed

    # Timing
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Cloud Tasks metadata
    cloud_task_name: Optional[str]  # GCP task resource name for deduplication
```

### Task Types

| Type | Parameters | Result |
|------|------------|--------|
| `create_doc` | `title`, `content`, `template_id?` | `{doc_id, url}` |
| `create_slides` | `title`, `slides[]`, `template_id?` | `{presentation_id, url}` |
| `create_sheet` | `title`, `data[]`, `template_id?` | `{spreadsheet_id, url}` |
| `send_email` | `to`, `subject`, `body`, `cc?`, `bcc?` | `{message_id, status}` |
| `send_sms` | `to`, `body` | `{message_sid, status}` |
| `export_pdf` | `doc_id`, `filename` | `{file_id, url}` |

---

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  ┌──────────────┐    ┌─────────────────┐    ┌───────────────┐  │
│  │   Chat UI    │    │  Neural Config  │    │  Task Monitor │  │
│  │              │    │   (Settings)    │    │    Panel      │  │
│  └──────┬───────┘    └─────────────────┘    └───────┬───────┘  │
│         │                                           │           │
└─────────┼───────────────────────────────────────────┼───────────┘
          │ POST /chat                                │ GET /tasks
          │                                           │ SSE /tasks/stream
          ▼                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND (Cloud Run)                 │
│                                                                  │
│  ┌─────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│  │  chat.py    │──▶│  task_service   │──▶│ Cloud Tasks API  │  │
│  │             │   │    .py          │   │   (enqueue)      │  │
│  └─────────────┘   └─────────────────┘   └──────────────────┘  │
│                                                  │               │
│  ┌─────────────────────────────────────┐         │               │
│  │    POST /tasks/execute/{task_id}    │◀────────┘               │
│  │    (Cloud Tasks HTTP callback)      │                         │
│  └──────────────┬──────────────────────┘                         │
│                 │                                                 │
│                 ▼                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Task Executor                           │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │   │
│  │  │ DocTask │  │EmailTask│  │SlideTask│  │ SheetTask   │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FIRESTORE                                 │
│  ┌─────────┐  ┌──────────┐  ┌───────────────┐  ┌────────────┐  │
│  │  users  │  │ sessions │  │     tasks     │  │   others   │  │
│  └─────────┘  └──────────┘  └───────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Task Management Router: `/tasks`

```python
# backend/routers/tasks.py

@router.post("/")
def create_task(request: CreateTaskRequest) -> TaskResponse:
    """Create a task and enqueue it for execution."""
    pass

@router.get("/")
def list_tasks(user_id: str, status: Optional[str] = None) -> list[TaskResponse]:
    """List tasks for a user, optionally filtered by status."""
    pass

@router.get("/{task_id}")
def get_task(task_id: str, user_id: str) -> TaskResponse:
    """Get details of a specific task."""
    pass

@router.delete("/{task_id}")
def cancel_task(task_id: str, user_id: str) -> dict:
    """Cancel a pending task (cannot cancel running tasks)."""
    pass

@router.post("/execute/{task_id}")
def execute_task(task_id: str, request: Request) -> dict:
    """
    Cloud Tasks calls this endpoint to execute a task.
    Validates OIDC token from Cloud Tasks service account.
    """
    pass

@router.get("/stream")
def stream_task_updates(user_id: str) -> StreamingResponse:
    """SSE endpoint for real-time task status updates."""
    pass
```

---

## Execution Flow

### 1. Task Creation (from Chat)

```python
# In chat.py tool execution
if tool_name in ASYNC_TASK_TOOLS:
    # Create task in Firestore
    task = Task(
        user_id=request.user_id,
        session_id=session.session_id,
        task_type=tool_name,
        parameters=tool_args,
        status="pending"
    )
    task_service.create_task(task)

    # Enqueue to Cloud Tasks
    task_service.enqueue(task.task_id)

    # Return immediate response to LLM
    tool_result = f"Task queued: {task.task_id}. User will be notified when complete."
```

### 2. Task Execution (Cloud Tasks callback)

```python
# POST /tasks/execute/{task_id}
def execute_task(task_id: str):
    task = get_task(task_id)

    # Update status
    update_task(task_id, status="running", started_at=now())

    try:
        # Execute based on task type
        executor = TASK_EXECUTORS[task.task_type]
        result = executor.execute(task.user_id, task.parameters)

        # Mark completed
        update_task(task_id, status="completed", result=result, completed_at=now())

    except Exception as e:
        # Mark failed (Cloud Tasks will retry based on config)
        update_task(task_id, status="failed", error=str(e))
        raise  # Let Cloud Tasks handle retry
```

### 3. Real-time Updates (SSE)

```python
# GET /tasks/stream?user_id=xxx
async def stream_task_updates(user_id: str):
    # Use Firestore real-time listeners
    def on_snapshot(docs, changes, read_time):
        for change in changes:
            if change.type.name == 'MODIFIED':
                yield format_sse_event("task_update", change.document.to_dict())

    # Subscribe to user's tasks
    query = db.collection('tasks').where('user_id', '==', user_id)
    query.on_snapshot(on_snapshot)
```

---

## Cloud Tasks Configuration

### Queue Settings (Terraform/gcloud)

```bash
gcloud tasks queues create bianca-task-queue \
    --location=us-central1 \
    --max-dispatches-per-second=10 \
    --max-concurrent-dispatches=5 \
    --max-attempts=3 \
    --min-backoff=10s \
    --max-backoff=300s
```

### Task Creation

```python
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

def enqueue_task(task_id: str, delay_seconds: int = 0):
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(PROJECT_ID, LOCATION, QUEUE_NAME)

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{BACKEND_URL}/tasks/execute/{task_id}",
            "oidc_token": {
                "service_account_email": TASKS_SERVICE_ACCOUNT,
            },
        }
    }

    if delay_seconds > 0:
        d = datetime.utcnow() + timedelta(seconds=delay_seconds)
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(d)
        task["schedule_time"] = timestamp

    response = client.create_task(parent=parent, task=task)
    return response.name
```

---

## Frontend: Task Monitor UI

### Location: Neural Config → Tasks Tab (NEW)

```jsx
// Tab content for task monitoring
function TasksTab({ userId }) {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all'); // all, pending, running, completed, failed

  // Load initial tasks
  useEffect(() => {
    getTasks(userId).then(setTasks);
  }, [userId]);

  // Subscribe to real-time updates
  useEffect(() => {
    const eventSource = new EventSource(`/tasks/stream?user_id=${userId}`);
    eventSource.addEventListener('task_update', (e) => {
      const updated = JSON.parse(e.data);
      setTasks(prev => prev.map(t => t.task_id === updated.task_id ? updated : t));
    });
    return () => eventSource.close();
  }, [userId]);

  return (
    <div className="tasks-panel">
      <FilterBar filter={filter} onChange={setFilter} />
      <TaskList tasks={filtered} />
    </div>
  );
}
```

### Task Card UI

```
┌──────────────────────────────────────────────────────────┐
│  📄 Create Document: Q3 Strategy Report                  │
│  ─────────────────────────────────────────────────────── │
│  Status: ████████░░ 80% — Applying formatting...         │
│  Started: 2 minutes ago                                  │
│                                                          │
│  [View Details]                              [Cancel]    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  ✅ Send Email: Meeting Follow-up                        │
│  ─────────────────────────────────────────────────────── │
│  Completed: 5 minutes ago                                │
│  Sent to: john@example.com                               │
│                                                          │
│  [View Result]                                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  ❌ Create Slides: Product Roadmap                       │
│  ─────────────────────────────────────────────────────── │
│  Failed: Template not found                              │
│  Attempted: 3 times                                      │
│                                                          │
│  [Retry]                           [View Error Details]  │
└──────────────────────────────────────────────────────────┘
```

---

## File Structure

```
backend/
├── routers/
│   └── tasks.py              # Task CRUD + execute endpoint
├── services/
│   └── task_service.py       # Task creation, enqueueing, execution logic
├── executors/
│   ├── __init__.py
│   ├── base.py               # BaseTaskExecutor class
│   ├── doc_executor.py       # Google Docs creation
│   ├── slides_executor.py    # Google Slides creation
│   ├── sheet_executor.py     # Google Sheets creation
│   └── email_executor.py     # Email sending
└── models.py                 # Add Task model

frontend/src/
├── api/
│   └── client.js             # Add task API functions
├── pages/
│   └── NeuralConfig.jsx      # Add Tasks tab
└── components/
    └── Tasks/
        ├── TasksTab.jsx
        ├── TaskCard.jsx
        ├── TaskDetails.jsx
        └── Tasks.css
```

---

## Development vs Production

### Local Development (No Cloud Tasks)

For local development without Cloud Tasks setup, use a fallback mode:

```python
# task_service.py
USE_CLOUD_TASKS = os.getenv("USE_CLOUD_TASKS", "false").lower() == "true"

def enqueue_task(task_id: str):
    if USE_CLOUD_TASKS:
        return _enqueue_cloud_tasks(task_id)
    else:
        # Fallback: execute in background thread
        import threading
        thread = threading.Thread(target=execute_task_sync, args=(task_id,))
        thread.start()
```

### Production (Google Cloud Run + Cloud Tasks)

```yaml
# Cloud Run service.yaml
spec:
  template:
    spec:
      containers:
        - image: gcr.io/PROJECT/bianca-backend
          env:
            - name: USE_CLOUD_TASKS
              value: "true"
            - name: CLOUD_TASKS_QUEUE
              value: "bianca-task-queue"
            - name: TASKS_SERVICE_ACCOUNT
              value: "cloud-tasks@PROJECT.iam.gserviceaccount.com"
```

---

## Security Considerations

1. **OIDC Token Validation**: The `/tasks/execute/{task_id}` endpoint validates that requests come from Cloud Tasks service account only.

2. **User Authorization**: Tasks are always associated with a user_id. Execution uses that user's OAuth tokens.

3. **Rate Limiting**: Cloud Tasks queue has built-in rate limiting. Frontend should also debounce rapid task creation.

4. **Sensitive Data**: Task parameters are stored in Firestore. Ensure email bodies and document content are not logged at DEBUG level.

---

## Implementation Priority

### Phase 1: Core Infrastructure (MVP)
1. Add `Task` model to `models.py`
2. Create `backend/routers/tasks.py` with basic CRUD
3. Create `backend/services/task_service.py` with thread-based execution (dev mode)
4. Add Tasks tab to Neural Config with basic list view

### Phase 2: Real Async Execution
5. Implement Cloud Tasks integration
6. Add SSE endpoint for real-time updates
7. Update frontend for live updates

### Phase 3: Full Feature Set
8. Add all task executors (docs, slides, sheets, email)
9. Integrate with chat.py tool execution
10. Add retry UI and error handling

### Phase 4: Polish
11. Task cancellation
12. Notification when task completes (toast/badge)
13. Task history with pagination
14. Export task logs

---

## Estimated Implementation Time

| Component | Effort |
|-----------|--------|
| Firestore Task model | 30 min |
| `/tasks` router (CRUD) | 1 hour |
| Task service (local mode) | 1 hour |
| Tasks tab UI (basic) | 2 hours |
| Cloud Tasks integration | 2 hours |
| SSE real-time updates | 1 hour |
| Task executors (4 types) | 2 hours |
| Chat integration | 1 hour |
| **Total MVP** | **~10 hours** |
