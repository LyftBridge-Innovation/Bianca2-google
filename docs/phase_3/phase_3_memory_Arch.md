# Phase 3 — Memory Architecture
> AI Chief of Staff · Locked Design · Ready for Implementation

---

## Overview

Phase 3 adds persistent memory to the system. After Phase 3 is complete, the assistant remembers what happened across sessions, across modalities, and across days. Every chat message will be enriched with relevant memories pulled from Vertex AI Search before being sent to the LLM.

Phase 3 is split into 3 sub-phases:

| Sub-phase | What gets built |
|---|---|
| **3A** | Firestore collections + session management |
| **3B** | Summarization pipeline + memory writing |
| **3C** | Vertex AI Search integration + memory injection into chat |

Do not start 3B until 3A is fully tested. Do not start 3C until 3B is fully tested.

---

---

# Phase 3A — Firestore Collections + Session Management

## Collections Overview

There are 5 Firestore collections in total.

| Collection | Purpose |
|---|---|
| `users` | User profile — one document per user |
| `sessions` | Raw chat history — one document per conversation session |
| `event_memories` | Long-term event-based memory extracted from sessions |
| `entity_memories` | Long-term entity-based memory extracted from sessions |
| `tool_action_log` | Every action Bianca took on the user's behalf |

---

## Collection: `users`

One document per user. Document ID is the `user_id`.

```
users/{user_id}
```

| Field | Type | Description |
|---|---|---|
| `user_id` | string | Unique user identifier |
| `email` | string | User's Google account email |
| `full_name` | string | From onboarding form |
| `job_title` | string | From onboarding form |
| `company` | string | From onboarding form |
| `timezone` | string | From onboarding form e.g. "America/Chicago" |
| `google_refresh_token` | string | Stored securely — used for Gmail and Calendar API calls |
| `assistant_name` | string | Read from config, stored here for reference. Default: set in config.py |
| `created_at` | timestamp | Account creation time |
| `updated_at` | timestamp | Last profile update |

> **Note for agent:** `timezone` is critical for all calendar operations. Every time the AI creates or reads a calendar event, it must convert times using this field. Never assume UTC.

---

## Collection: `sessions`

One document per conversation session. A session is one continuous conversation — a chat session, or a phone call transcript. All modalities write to this same collection.

```
sessions/{session_id}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Auto-generated unique ID |
| `user_id` | string | Reference to the user |
| `modality` | string | One of: `chat`, `voice`, `email`, `sms` |
| `status` | string | One of: `active`, `summarized` |
| `messages` | array | Ordered list of message objects (see below) |
| `tool_calls` | array | Ordered list of tool call objects (see below) |
| `created_at` | timestamp | When the session started |
| `last_activity_at` | timestamp | Updated on every new message — used for inactivity detection |
| `summarized_at` | timestamp | When summarization was triggered. Null if not yet summarized |
| `summary_event_id` | string | Reference to the event_memories document created from this session |
| `summary_entity_id` | string | Reference to the entity_memories document created from this session |

**Message object structure (inside `messages` array):**

| Field | Type | Description |
|---|---|---|
| `role` | string | One of: `user`, `assistant` |
| `content` | string | The message text |
| `timestamp` | timestamp | When this message was sent |

**Tool call object structure (inside `tool_calls` array):**

| Field | Type | Description |
|---|---|---|
| `tool_name` | string | e.g. `send_email`, `decline_event`, `create_event` |
| `parameters` | map | The inputs passed to the tool |
| `result` | string | Short description of outcome e.g. "Email sent successfully" |
| `timestamp` | timestamp | When the tool was called |

> **Note for agent:** Every time a tool executes successfully, write to both `tool_calls` in the session AND to the `tool_action_log` collection. These serve different purposes — tool_calls is session-scoped context, tool_action_log is the global auditable history of what Bianca did.

---

## Collection: `tool_action_log`

Global log of every action Bianca took on behalf of the user. Queryable independently of sessions.

```
tool_action_log/{log_id}
```

| Field | Type | Description |
|---|---|---|
| `log_id` | string | Auto-generated unique ID |
| `user_id` | string | Reference to the user |
| `session_id` | string | Reference to the session this action happened in |
| `tool_name` | string | e.g. `send_email`, `decline_event`, `create_event` |
| `human_readable` | string | e.g. "Bianca declined a meeting with Sarah on Feb 19" |
| `parameters` | map | Full parameters passed to the tool |
| `result` | string | Short outcome description |
| `timestamp` | timestamp | When the action was taken |
| `modality` | string | Which channel triggered this action: `chat`, `voice`, etc. |

> **Note for agent:** The `human_readable` field is generated by a short LLM call at the time of the tool action. Prompt: *"Write one sentence describing what Bianca just did, from the user's perspective. Use past tense. Start with 'Bianca'."* Keep it under 20 words.

---

## Session Lifecycle

A session moves through these states:

```
created (status: active)
        ↓
messages accumulate, last_activity_at updates on each message
        ↓
summarization triggered by one of 3 conditions:
  - User opens a new chat session
  - User explicitly closes the chat
  - Inactivity timer fires (Phase 6 — server-side scheduler, skip for now)
        ↓
summarization runs (Phase 3B)
        ↓
status → "summarized", summarized_at set, summary IDs written back
```

> **Note for agent:** For Phase 3A, implement session creation, message appending, and the status field. The summarization trigger logic (new chat opens → mark old session for summarization) is implemented in Phase 3B.

---

## Phase 3A Acceptance Criteria

| Test | Pass Condition |
|---|---|
| Session creation | POST /chat creates a new session document in Firestore with status: active |
| Message persistence | Every message exchanged is appended to the session's messages array with correct role and timestamp |
| Tool call persistence | Every tool execution appends to both session tool_calls and tool_action_log |
| human_readable generation | tool_action_log entry contains a valid Bianca-prefixed sentence |
| last_activity_at | Updates correctly on every new message |
| User document | User profile document exists and timezone field is populated |
| New session trigger | Opening a new chat creates a new session_id, previous session status stays active (summarization comes in 3B) |

---

---

# Phase 3B — Summarization Pipeline

## Overview

When summarization is triggered, the system reads the full session from Firestore, makes 2 LLM calls in parallel (one for event memory, one for entity memory), writes 2 documents to Firestore, pushes both to Vertex AI Search, then updates the session status to `summarized`.

---

## Summarization Trigger

Summarization is triggered when:
1. User opens a new chat — the previous active session (if any) is passed to the summarization function
2. User explicitly closes chat — same as above

The inactivity trigger (5 min timer via APScheduler) is **deferred to Phase 6**. For now, only manual triggers.

The summarization function signature:
```
summarize_session(user_id: str, session_id: str) → None
```

This function is called asynchronously as a background task in FastAPI so it does not block the user opening their new chat.

---

## LLM Call 1 — Event Memory

**What it does:** Extracts a summary of things that *happened* in the session.

**Input to LLM:** Full message history from the session + list of tool actions taken.

**System prompt direction:**
Extract only concrete events, actions, and outcomes from this conversation. Include things the user asked for, things Bianca did, meetings discussed, emails sent, decisions made. Write as 3-7 bullet points maximum. Be specific — include names, dates, and outcomes where available. Do not include preferences or personality observations.

**Output:** Plain text, 3-7 bullet points.

**Example output:**
```
- User asked Bianca to decline a meeting with John scheduled for Feb 20
- Bianca declined the meeting and sent John a message saying the user was unavailable
- User asked for a summary of unread emails from Sarah
- Bianca retrieved 3 emails from Sarah, all related to the Acme Corp proposal
- User asked Bianca to draft a reply to Sarah's latest email for review
```

---

## Collection: `event_memories`

```
event_memories/{memory_id}
```

| Field | Type | Description |
|---|---|---|
| `memory_id` | string | Auto-generated unique ID |
| `user_id` | string | Reference to the user |
| `session_id` | string | Reference to the source session |
| `type` | string | Always `event` |
| `content` | string | The LLM-generated summary text |
| `is_update` | boolean | False for original, True if this supersedes a previous memory |
| `supersedes_memory_id` | string | If is_update is True, the memory_id this replaces. Null otherwise |
| `created_at` | timestamp | When this memory was created |
| `vertex_doc_id` | string | The document ID in Vertex AI Search — stored for reference |

---

## LLM Call 2 — Entity Memory

**What it does:** Extracts facts about people, companies, and things mentioned in the session.

**Input to LLM:** Full message history from the session.

**System prompt direction:**
Extract only factual information about people, companies, or recurring topics mentioned in this conversation. Include relationships (e.g. "John is the user's manager"), important contacts, organizations, and any named projects or recurring themes. Write as 3-7 bullet points maximum. Do not include events or what happened — only who/what things are.

**Output:** Plain text, 3-7 bullet points.

**Example output:**
```
- Sarah is the user's client at Acme Corp, working on a proposal
- John appears to be a colleague or manager who requested the Feb 20 meeting
- Acme Corp proposal is an ongoing project the user is actively managing
- User's calendar is managed via Google Calendar with primary calendar ID
```

---

## Collection: `entity_memories`

```
entity_memories/{memory_id}
```

| Field | Type | Description |
|---|---|---|
| `memory_id` | string | Auto-generated unique ID |
| `user_id` | string | Reference to the user |
| `session_id` | string | Reference to the source session |
| `type` | string | Always `entity` |
| `content` | string | The LLM-generated summary text |
| `is_update` | boolean | False for original, True if this supersedes a previous memory |
| `supersedes_memory_id` | string | If is_update is True, the memory_id this replaces. Null otherwise |
| `created_at` | timestamp | When this memory was created |
| `vertex_doc_id` | string | The document ID in Vertex AI Search — stored for reference |

---

## Immutability Rule

**Never update or delete a memory document.** If a session is updated and re-summarized, create new documents with `is_update: True` and `supersedes_memory_id` pointing to the old ones. The old documents remain in Firestore and Vertex AI Search untouched. The RAG search naturally favors newer documents via the recency filter. This makes the memory system append-only and fully auditable.

---

## Vertex AI Search Push

Immediately after writing to Firestore (synchronously, same function call), push the document to Vertex AI Search.

Each document pushed to Vertex AI Search contains:
- `id` — the Firestore memory_id
- `content` — the summary text (this is what gets embedded)
- `user_id` — for filtering search results to the correct user
- `type` — `event` or `entity`
- `created_at` — ISO 8601 string, used for recency filtering

> **Note for agent:** Vertex AI Search is configured with one datastore. All memory types live in the same datastore, filtered by `type` and `user_id` at query time. Do not create separate datastores per memory type.

---

## Phase 3B Acceptance Criteria

| Test | Pass Condition |
|---|---|
| Summarization trigger | Opening a new chat triggers summarization of the previous session as a background task |
| Event memory created | event_memories document exists in Firestore after summarization |
| Entity memory created | entity_memories document exists in Firestore after summarization |
| Session updated | Session status is `summarized`, summarized_at is set, summary_event_id and summary_entity_id are populated |
| Vertex push | Both memory documents appear in Vertex AI Search datastore after summarization |
| Immutability | Re-summarizing a session creates new documents with is_update: True, old documents untouched |
| Background task | New chat opens immediately without waiting for summarization to complete |

---

---

# Phase 3C — Memory Injection into Chat

## Overview

Every time the user sends a message, before calling the LLM, the system queries Vertex AI Search for relevant memories and injects them into the system prompt. If no memories are found, the AI proceeds without memory context and asks for clarification only if the message is completely ambiguous without it.

---

## Memory Retrieval Flow

On every incoming user message:

```
1. Take user's raw message text
2. Query Vertex AI Search with the message text as the search query
   - Filter: user_id = current user
   - Filter: created_at >= 30 days ago (recency window)
   - Return top 5 results across both event and entity memory types
3. If results found → inject into system prompt (see below)
4. If 0 results found → proceed without memory, AI asks clarification only if message is unresolvable
```

> **On the recency window:** Default is 30 days. If fewer than 3 results are returned within 30 days, automatically expand the window to 90 days and retry once. This handles new users or low-activity periods gracefully.

---

## System Prompt Memory Injection Format

The retrieved memories are injected into the system prompt as a dedicated section, placed before the conversation history:

```
## What you remember about this user

### Recent Events
- [event memory bullet 1]
- [event memory bullet 2]
- [event memory bullet 3]

### People and Entities
- [entity memory bullet 1]
- [entity memory bullet 2]

---
[rest of system prompt continues]
```

Event and entity memories are separated in the injected block so the LLM can easily distinguish between "what happened" and "who things are."

---

## Clarification Behavior

If Vertex AI Search returns 0 results AND the user's message cannot be resolved without context (e.g. "what about that thing from last time"), the AI should respond naturally asking what they're referring to — not with a technical error or a robotic "I found no memories." It should feel like a natural "Could you remind me what you're referring to?" response.

If the message can be resolved without memory (e.g. "what's on my calendar today"), proceed directly with tool calls regardless of memory results.

---

## Updated `/chat` Endpoint Flow

```
receive user message
        ↓
update last_activity_at on current session
        ↓
query Vertex AI Search for top 5 relevant memories (user-scoped, last 30 days)
        ↓
build system prompt with memory injection block
        ↓
call Gemini with full system prompt + current session message history
        ↓
stream response back to user
        ↓
append user message + assistant response to session messages array
        ↓
if tool was called → write to session tool_calls + tool_action_log
```

---

## Phase 3C Acceptance Criteria

| Test | Pass Condition |
|---|---|
| Memory retrieval | Sending a message triggers a Vertex AI Search query scoped to the correct user |
| Injection | Relevant memories appear in the system prompt before the LLM is called |
| Cross-session continuity | Start a new session, reference something from a previous one — AI responds with correct context |
| Zero results handling | With no memories, AI proceeds normally for tool-resolvable messages |
| Zero results clarification | With no memories and an ambiguous message, AI asks naturally for clarification |
| Recency expansion | Manually create a memory older than 30 days, verify the 90-day fallback retrieves it |
| Separation | Event and entity memories appear in separate sections in the injected prompt |
| Top 5 cap | Verify no more than 5 memory entries are injected regardless of how many exist |

---

---

# Summary — What the Coding Agent Builds

| Phase | Deliverable |
|---|---|
| **3A** | 5 Firestore collections with correct schemas. Session creation and message persistence wired into /chat. Tool action logging on every tool execution. |
| **3B** | Summarization function with 2 parallel LLM calls. Writes to event_memories and entity_memories. Pushes to Vertex AI Search synchronously. Triggered as background task when new chat opens. Append-only immutability enforced. |
| **3C** | Memory retrieval on every message. System prompt injection with event/entity separation. Recency window with 30-day default and 90-day fallback. Clarification behavior for zero-result ambiguous messages. |

---

## Things Deliberately Deferred (Do Not Implement in Phase 3)

- Inactivity timer / APScheduler — deferred to Phase 6
- Scheduled/pending actions task queue — deferred to Phase 6
- Voice transcript processing — deferred to Phase 5
- SMS and email modalities — deferred to Phase 5/6
- Preference-based memory (third memory type) — deferred, may never be needed
- Freshness boosting in RAG — deferred, use pure semantic search for now


## Important things noted down by developer and senior developer

- The most likely thing to trip up the agent in 3B is the async background task for summarization. FastAPI's BackgroundTasks is straightforward but make sure the agent doesn't accidentally block the new chat response waiting for summarization to finish. The user should get their new chat instantly.

- The most likely thing to trip up the agent in 3C is Vertex AI Search setup — it requires a datastore to be created in Google Cloud console before any code can push to it. Have the agent document the manual setup steps before writing the push logic, otherwise you'll hit auth and datastore-not-found errors that look confusing.

- One thing to watch — the human_readable field in tool_action_log requires a small LLM call per tool execution. Make sure the agent uses your cheapest Gemini model for this (Gemini Flash Lite or equivalent), not the main chat model. It's a one-liner prompt, no need to burn credits on it.