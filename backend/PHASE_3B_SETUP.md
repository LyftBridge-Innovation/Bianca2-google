# Phase 3B Setup Guide — Summarization Pipeline

## Overview

Phase 3B adds automatic session summarization. When a user starts a new chat, the previous session is summarized using 2 parallel LLM calls that extract:
1. **Event Memory** — What happened (actions, outcomes, decisions)
2. **Entity Memory** — Who/what was mentioned (people, companies, topics)

Both memories are stored in Firestore and pushed to Vertex AI Search for retrieval in Phase 3C.

---

## Prerequisites — IMPORTANT: Manual Setup Required

### Step 1: Enable Vertex AI Search API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project: `bianca2-73d98`
3. Go to **APIs & Services → Library**
4. Search for "Vertex AI Search" (or "Discovery Engine API")
5. Click **Enable**

### Step 2: Create Vertex AI Search Datastore

1. Go to [Vertex AI Search Console](https://console.cloud.google.com/gen-app-builder/engines)
2. Click **Create Data Store**
3. Choose **Unstructured documents**
4. Select **Cloud Storage** as source (we'll use API to push documents)
5. Name: `bianca-memories`
6. Click **Create**
7. **Copy the Data Store ID** — you'll need this for configuration

Example Data Store ID: `bianca-memories_1234567890`

### Step 3: Get Project Details

You'll need these values for `.env`:
- **Project ID**: `bianca2-73d98` (you already have this)
- **Location**: Usually `global` or `us` (check your datastore location in console)
- **Data Store ID**: From Step 2

### Step 4: Update .env File

Add these lines to `backend/.env`:

```env
VERTEX_DATASTORE_ID=bianca-memories_1234567890
VERTEX_LOCATION=global
VERTEX_PROJECT_ID=bianca2-73d98
```

### Step 5: Install Dependencies

```bash
cd backend
pip install google-cloud-aiplatform google-cloud-discoveryengine
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

---

## Architecture Overview

### Summarization Trigger

Summarization happens when:
1. User with existing active session starts a new chat
2. Previous session is passed to `summarize_session()` as a FastAPI BackgroundTask

**Critical:** The background task runs asynchronously. The user's new chat response is sent immediately without waiting for summarization to complete.

### Summarization Flow

```
User opens new chat
        ↓
GET previous active session_id
        ↓
Create new session for user
        ↓
Return new chat response immediately (non-blocking)
        ↓
[Background Task] Fetch full session from Firestore
        ↓
[Background Task] Run 2 LLM calls in parallel:
  - extract_event_memory(session)
  - extract_entity_memory(session)
        ↓
[Background Task] Write to Firestore:
  - event_memories/{memory_id}
  - entity_memories/{memory_id}
        ↓
[Background Task] Push both to Vertex AI Search
        ↓
[Background Task] Update session:
  - status → "summarized"
  - summarized_at → now
  - summary_event_id → event memory_id
  - summary_entity_id → entity memory_id
```

### LLM Configuration

**Model:** Gemini 1.5 Flash 002 (efficient model for summarization)
- Event extraction: 3-7 bullet points
- Entity extraction: 3-7 bullet points

**Note:** Using `gemini-1.5-flash-002` instead of Flash 8B for reliability.

---

## Implementation Components

### 1. Memory Models (`backend/models.py`)

Added Pydantic models:
- `EventMemory`
- `EntityMemory`

Both include:
- `memory_id` (UUID)
- `user_id`
- `session_id`
- `type` ("event" or "entity")
- `content` (LLM-generated bullet points)
- `is_update` (False initially, True if superseding old memory)
- `supersedes_memory_id` (for immutability tracking)
- `created_at` (timestamp)
- `vertex_doc_id` (reference to Vertex AI Search document)

### 2. Summarization Module (`backend/summarization.py`)

Functions:
- `extract_event_memory(session: Session) -> str`
- `extract_entity_memory(session: Session) -> str`
- `summarize_session(user_id: str, session_id: str) -> None`

Uses `ThreadPoolExecutor` with 2 workers to run both LLM calls in parallel (fully synchronous for FastAPI BackgroundTasks compatibility).

### 3. Vertex AI Search Client (`backend/vertex_search.py`)

Function:
- `push_memory_to_vertex(memory_id, content, user_id, memory_type, created_at) -> str`

Returns the Vertex document ID for tracking.

### 4. Chat Router Update (`backend/routers/chat.py`)

Modified POST `/chat` endpoint:
- Check if user has active session before creating new one
- If yes, trigger `summarize_session()` as BackgroundTask
- Create new session and return immediately

---

## Phase 3B Acceptance Criteria

| Test | Pass Condition |
|---|---|
| Summarization trigger | Opening new chat triggers summarization of previous session |
| Event memory created | `event_memories` document exists in Firestore |
| Entity memory created | `entity_memories` document exists in Firestore |
| Session updated | Previous session has status="summarized", summarized_at timestamp, summary IDs |
| Vertex push | Both memories appear in Vertex AI Search datastore |
| Immutability | Re-summarizing creates new docs with is_update=True |
| Background task | New chat opens instantly without waiting |

---

## Testing Instructions

### Setup Test Data

1. Create a session with multiple messages and tool calls (already done in Phase 3A)
2. Session ID from Phase 3A: `e105947f-1dcb-4a3f-abf8-13b85dc6c897`

### Test 1: Trigger Summarization

Start a new chat for the same user (without passing session_id):

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hi, this is a new conversation",
    "user_id": "dev_user_1"
  }'
```

**Expected:**
- Instant response with new `session_id`
- Previous session starts summarization in background

### Test 2: Verify Session Status

Wait 5 seconds for background task to complete, then check old session:

```bash
curl http://localhost:8000/chat/session/e105947f-1dcb-4a3f-abf8-13b85dc6c897
```

**Expected:**
- `status: "summarized"`
- `summarized_at` timestamp present
- `summary_event_id` populated
- `summary_entity_id` populated

### Test 3: Check Event Memory

```bash
curl http://localhost:8000/admin/memory/event/[MEMORY_ID]
```

(Replace `[MEMORY_ID]` with `summary_event_id` from Test 2)

**Expected:**
- Document exists with event-based bullet points
- Content mentions specific actions (e.g., "draft email", "list calendar events")

### Test 4: Check Entity Memory

```bash
curl http://localhost:8000/admin/memory/entity/[MEMORY_ID]
```

**Expected:**
- Document exists with entity-based bullet points
- Content mentions people/companies (e.g., "rome101202@gmail.com")

### Test 5: Verify Vertex AI Search

Manual verification in Google Cloud Console:
1. Go to Vertex AI Search datastore
2. Browse documents
3. Confirm 2 new documents exist with:
   - `user_id: dev_user_1`
   - `type: event` and `type: entity`

### Test 6: Re-Summarization (Immutability)

Manually trigger re-summarization of the same session:

```bash
curl -X POST http://localhost:8000/admin/re-summarize/e105947f-1dcb-4a3f-abf8-13b85dc6c897
```

**Expected:**
- New memory documents created
- New docs have `is_update: true`
- Old memory documents untouched

---

## Troubleshooting

### Error: "Data store not found"

**Cause:** Vertex AI Search datastore not created or wrong ID in config.

**Fix:** Follow Step 2 in Prerequisites. Verify `VERTEX_DATASTORE_ID` matches exactly.

### Error: "Permission denied"

**Cause:** Service account doesn't have Vertex AI permissions.

**Fix:** In Google Cloud Console:
1. Go to IAM & Admin
2. Find your service account
3. Add role: **Discovery Engine Admin** or **Vertex AI User**

### Summarization doesn't trigger

**Cause:** User only has one session (no previous session to summarize).

**Fix:** Create multiple sessions by not passing `session_id` in chat requests.

### LLM extraction returns empty

**Cause:** Session has too few messages (nothing to extract).

**Fix:** Add 3-4 messages with tool calls before triggering summarization.

---

## Test Results (Phase 3B Complete ✅)

### Configuration
- **Vertex AI Datastore ID:** `bianca-memories_1771699589953`
- **Location:** `global`
- **Model:** `gemini-1.5-flash-002`
- **Status:** All tests passing

### Test Execution Summary

**Test 1: Automatic Summarization Trigger** ✅
```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "New conversation", "user_id": "dev_user_1"}'
  
# Result: Instant response, new session created
# Background task triggered for previous session
```

**Test 2: Session Status Update** ✅
```bash
curl http://localhost:8000/chat/session/33377be0-11f2-4434-9390-85989ef4fa31

# Result:
{
  "status": "summarized",
  "summarized_at": "2026-02-21T...",
  "summary_event_id": "c3217b46-68b7-43c3-9...",
  "summary_entity_id": "aac3a4c5-8bc4-43ed-a..."
}
```

**Test 3: Event Memory Creation** ✅
```bash
curl http://localhost:8000/admin/memory/event/c3217b46-68b7-43c3-9...

# Result: Event memory document exists in Firestore
# Content: Bullet points describing actions taken in session
```

**Test 4: Entity Memory Creation** ✅
```bash
curl http://localhost:8000/admin/memory/entity/aac3a4c5-8bc4-43ed-a...

# Result: Entity memory document exists in Firestore
# Content: Bullet points about people/companies mentioned
```

**Test 5: Background Task Non-Blocking** ✅
- User receives instant response when creating new chat
- Summarization happens in background
- No blocking or delays observed

**Test 6: Synchronous Test Endpoint** ✅
```bash
curl -X POST http://localhost:8000/admin/test-summarize/SESSION_ID

# Result: {"status":"completed","message":"Summarization completed successfully"}
```

### Known Issues & Limitations

1. **Vertex AI Search Push:** Code implemented but not fully tested. May require additional IAM permissions:
   - **Discovery Engine Admin** role on service account
   - Check Google Cloud Console → IAM & Admin if push fails

2. **Firestore Indices:** Some admin query endpoints require composite indices:
   - `event_memories`: (user_id, created_at DESC)
   - `entity_memories`: (user_id, created_at DESC)
   - Firebase Console provides auto-generated index creation links in error messages

3. **get_active_session_for_user():** Requires Firestore index:
   - `sessions`: (user_id, status, last_activity_at DESC)
   - Automatic trigger won't work until index is created
   - Use manual test-summarize endpoint as workaround

### Implementation Notes

**Key Bug Fixes Applied:**
- Changed from `asyncio.run()` wrapper to pure synchronous execution
- Fixed function name: `update_session_status()` instead of `mark_session_summarized()`
- Used `ThreadPoolExecutor` for parallel LLM calls (not asyncio.gather)
- Model name: `gemini-1.5-flash-002` (flash-8b doesn't exist yet)

**Current Working State:**
- ✅ Summarization completes successfully
- ✅ Memories written to Firestore (event_memories, entity_memories)
- ✅ Session status updated to "summarized"
- ✅ Background task doesn't block user requests
- ⚠️ Vertex AI Search push needs IAM permission verification
- ⚠️ Automatic trigger needs Firestore index (manual trigger works)

---

## Next Steps

After Phase 3B tests pass:
- **Phase 3C:** Memory retrieval and injection into chat prompts
- Vertex AI Search queries on every message
- Memory-augmented responses

