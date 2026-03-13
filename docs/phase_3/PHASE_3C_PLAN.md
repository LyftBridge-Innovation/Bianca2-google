# Phase 3C Implementation Plan — Memory Injection into Chat

## Overview

Phase 3C adds memory retrieval to every chat message. Before sending the user's message to the LLM, the system queries Vertex AI Search for relevant memories and injects them into the system prompt.

**Goal:** Enable cross-session contextual awareness so the assistant remembers past conversations.

---

## Core Requirements

### 1. Memory Retrieval Flow
```
User sends message
        ↓
Query Vertex AI Search (semantic search)
        ↓
Filter: user_id = current user
Filter: created_at >= 30 days ago (recency window)
Return: Top 5 results (combined events + entities)
        ↓
If results < 3 → Expand window to 90 days, retry once
        ↓
Inject memories into system prompt
        ↓
Send to LLM with enriched context
```

### 2. System Prompt Injection Format
```markdown
## What you remember about this user

### Recent Events
- [event memory bullet 1]
- [event memory bullet 2]

### People and Entities
- [entity memory bullet 1]
- [entity memory bullet 2]

---
[rest of system prompt continues]
```

### 3. Graceful Degradation
- **0 results + tool-resolvable message** → Proceed directly with tool calls
- **0 results + ambiguous message** → Ask naturally for clarification (not technical error)
- **Vertex AI Search unavailable** → Log warning, proceed without memories

---

## Implementation Components

### Component 1: Update `vertex_search.py`
**File:** `backend/vertex_search.py`

**Function to implement:**
```python
def search_memories(
    query: str,
    user_id: str,
    max_results: int = 5,
    recency_days: int = 30
) -> list[dict]:
```

**Requirements:**
- Use Discovery Engine SearchServiceClient
- Build serving_config path from VERTEX_DATASTORE_ID
- Filter by user_id: `'user_id: ANY("{user_id}")'`
- Return list of dicts with: memory_id, content, type, created_at
- Handle empty results gracefully (return [])
- Log all queries and result counts

**Edge cases:**
- Datastore not configured → return []
- Search API error → return []
- No results → return []

**Already exists:** Stub implementation at line 92, needs completion

---

### Component 2: Create `memory_retrieval.py` (New File)
**File:** `backend/memory_retrieval.py`

**Purpose:** Orchestrate memory retrieval with fallback logic

**Function 1: `retrieve_memories_for_message()`**
```python
def retrieve_memories_for_message(
    user_message: str,
    user_id: str
) -> dict:
    """
    Retrieve relevant memories with automatic fallback.
    
    Returns:
        {
            "event_memories": [str],  # List of event bullet points
            "entity_memories": [str], # List of entity bullet points
            "total_count": int,
            "recency_window_days": int  # 30 or 90
        }
    """
```

**Logic:**
1. Query with 30-day window, max 5 results
2. If result count < 3:
   - Log: "Few results with 30-day window, expanding to 90 days"
   - Query again with 90-day window, max 5 results
3. Separate results by type (event vs entity)
4. Return structured dict

**Function 2: `format_memory_injection()`**
```python
def format_memory_injection(
    event_memories: list[str],
    entity_memories: list[str]
) -> str:
    """
    Format memories into system prompt injection block.
    
    Returns formatted string ready for prompt injection.
    """
```

**Format:**
```
## What you remember about this user

### Recent Events
- Event bullet 1
- Event bullet 2

### People and Entities
- Entity bullet 1
- Entity bullet 2
```

**Edge cases:**
- Empty events → Show "### Recent Events\n(No recent events recorded)"
- Empty entities → Show "### People and Entities\n(No entities recorded)"
- Both empty → Return empty string (don't inject section at all)

---

### Component 3: Update `routers/chat.py`
**File:** `backend/routers/chat.py`

**Changes needed:**

**1. Import memory retrieval:**
```python
from memory_retrieval import retrieve_memories_for_message, format_memory_injection
```

**2. Add memory retrieval before LLM call:**
```python
# After: messages.append(HumanMessage(content=request.message))
# Before: response = llm.invoke(messages)

# Retrieve memories
memory_data = retrieve_memories_for_message(
    user_message=request.message,
    user_id=request.user_id
)

# Inject into system prompt if memories exist
if memory_data["total_count"] > 0:
    memory_block = format_memory_injection(
        event_memories=memory_data["event_memories"],
        entity_memories=memory_data["entity_memories"]
    )
    
    # Update system message (first message in chain)
    original_system_prompt = CHIEF_OF_STAFF_SYSTEM_PROMPT
    enriched_system_prompt = f"{original_system_prompt}\n\n{memory_block}"
    messages[0] = SystemMessage(content=enriched_system_prompt)
    
    logger.info(f"Injected {memory_data['total_count']} memories (window: {memory_data['recency_window_days']} days)")
```

**3. Log memory retrieval stats:**
- Total memories injected
- Recency window used (30 or 90 days)
- Query text (truncated to 50 chars)

---

### Component 4: Update `config.py`
**File:** `backend/config.py`

**Add configuration:**
```python
# Memory retrieval configuration (Phase 3C)
MEMORY_RECENCY_DAYS_DEFAULT = int(os.getenv("MEMORY_RECENCY_DAYS_DEFAULT", "30"))
MEMORY_RECENCY_DAYS_FALLBACK = int(os.getenv("MEMORY_RECENCY_DAYS_FALLBACK", "90"))
MEMORY_MAX_RESULTS = int(os.getenv("MEMORY_MAX_RESULTS", "5"))
MEMORY_MIN_RESULTS_THRESHOLD = int(os.getenv("MEMORY_MIN_RESULTS_THRESHOLD", "3"))
```

**Why configurable?**
- Allows tuning without code changes
- Different users might need different windows
- Can adjust max results based on token limits

---

### Component 5: Admin Endpoints for Testing
**File:** `backend/routers/admin.py`

**Add testing endpoints:**

**1. Test Memory Retrieval:**
```python
@router.post("/test-memory-retrieval")
def test_memory_retrieval(query: str, user_id: str, recency_days: int = 30):
    """Test memory retrieval without going through chat."""
    from memory_retrieval import retrieve_memories_for_message
    
    result = retrieve_memories_for_message(query, user_id)
    return result
```

**2. View All Memories (paginated):**
```python
@router.get("/all-memories/{user_id}")
def get_all_memories(user_id: str, limit: int = 20):
    """Get all memories for debugging (bypasses indices)."""
    # Direct Firestore query without ordering
    event_docs = fs.db.collection('event_memories')\
        .where('user_id', '==', user_id)\
        .limit(limit)\
        .stream()
    
    entity_docs = fs.db.collection('entity_memories')\
        .where('user_id', '==', user_id)\
        .limit(limit)\
        .stream()
    
    return {
        "event_memories": [doc.to_dict() for doc in event_docs],
        "entity_memories": [doc.to_dict() for doc in entity_docs]
    }
```

---

## Testing Strategy

### Test Setup
1. Use existing session with summarized memories from Phase 3B
2. Create test messages that should trigger memory retrieval
3. Verify memories appear in system prompt

### Test 1: Cross-Session Memory Retrieval
```bash
# Session 1: User mentions "rome101202@gmail.com"
curl -X POST http://localhost:8000/chat/ \
  -d '{"message": "Draft email to rome101202@gmail.com", "user_id": "dev_user_1"}'

# Trigger summarization (start new session)
curl -X POST http://localhost:8000/chat/ \
  -d '{"message": "Hi", "user_id": "dev_user_1"}'

# Session 2: Reference should trigger memory
curl -X POST http://localhost:8000/chat/ \
  -d '{"message": "What was that email address I used before?", "user_id": "dev_user_1"}'
```

**Expected:** AI should reference rome101202@gmail.com from memory

### Test 2: Recency Window Fallback
```bash
# Query admin endpoint to see memory counts
curl http://localhost:8000/admin/test-memory-retrieval \
  -d '{"query": "email", "user_id": "dev_user_1", "recency_days": 30}'

# Should auto-expand to 90 days if < 3 results
```

**Expected:** If 30-day returns < 3, should automatically try 90-day

### Test 3: Zero Results Handling
```bash
# Create brand new user with no memories
curl -X POST http://localhost:8000/admin/init-test-user  # creates dev_user_1

# First message ever (no memories)
curl -X POST http://localhost:8000/chat/ \
  -d '{"message": "What is my calendar?", "user_id": "dev_user_2"}'
```

**Expected:** Should proceed directly with tool call, no memory injection

### Test 4: Ambiguous Message with No Memory
```bash
curl -X POST http://localhost:8000/chat/ \
  -d '{"message": "What about that thing we discussed?", "user_id": "dev_user_2"}'
```

**Expected:** Natural clarification like "Could you remind me what you're referring to?"

### Test 5: Memory Injection Format
```bash
# Check logs for memory injection
# Should see system prompt with "## What you remember about this user"
```

**Expected:** Memories formatted with clear event/entity separation

---

## Acceptance Criteria (Phase 3C)

| Test | Pass Condition |
|---|---|
| Memory retrieval | Every chat message triggers Vertex AI Search query |
| Injection | Memories appear in system prompt before LLM call |
| Cross-session continuity | AI references info from previous summarized sessions |
| Zero results (tool-resolvable) | Proceeds with tool calls without errors |
| Zero results (ambiguous) | Natural clarification request |
| Recency expansion | Automatically tries 90-day window if 30-day < 3 results |
| Event/entity separation | Memories grouped by type in prompt |
| Top 5 cap | Max 5 memories injected regardless of matches |
| Graceful degradation | Works without Vertex AI Search configured |
| Logging | All queries logged with result counts |

---

## Implementation Order

### Step 1: Complete `vertex_search.py` search function
- Implement `search_memories()` fully
- Test with direct calls (no chat flow)
- Verify Vertex AI Search returns results

### Step 2: Create `memory_retrieval.py`
- Implement `retrieve_memories_for_message()`
- Implement `format_memory_injection()`
- Add fallback logic (30→90 days)
- Unit test both functions

### Step 3: Update `chat.py` endpoint
- Add memory retrieval before LLM call
- Inject formatted memories into system prompt
- Add logging for observability

### Step 4: Add admin test endpoints
- `/test-memory-retrieval` for debugging
- `/all-memories/{user_id}` for inspection

### Step 5: Update config
- Add memory configuration variables
- Document in .env.example

### Step 6: Test all acceptance criteria
- Run through each test case
- Verify cross-session memory works
- Check logs for proper injection

### Step 7: Update documentation
- Add Phase 3C results to PHASE_3C_SETUP.md
- Document any issues found
- Add troubleshooting section

---

## Edge Cases & Considerations

### 1. Token Limits
- Max 5 memories prevents prompt overflow
- Each memory ~50-150 tokens
- Total injection: ~250-750 tokens
- Well within Gemini's 1M token context

### 2. Ambiguous vs Tool-Resolvable
**Ambiguous:** "What about that meeting?"
- No tool can resolve without more context
- Needs clarification

**Tool-resolvable:** "What's on my calendar today?"
- Direct tool call (list_calendar_events)
- Proceed even with 0 memories

**Implementation:** Let LLM handle naturally - don't add special logic

### 3. Memory Staleness
- 30-day default balances relevance vs coverage
- 90-day fallback ensures cold-start users get help
- Future: could add decay scoring

### 4. Multiple Sessions Same Day
- Memories created continuously
- Recency filter ensures freshest results
- Vertex AI Search handles semantic relevance

### 5. Vertex AI Search Latency
- Typical: 100-300ms per query
- Acceptable for chat use case
- Could add caching later (Phase 6)

---

## Success Metrics

**Functional:**
- ✅ Memory injection working in 100% of chats
- ✅ Zero Vertex AI Search errors
- ✅ Graceful handling of edge cases

**Quality:**
- ✅ AI successfully uses memories in responses
- ✅ Cross-session references work correctly
- ✅ No hallucinations about non-existent memories

**Performance:**
- ✅ Memory retrieval adds < 500ms to chat latency
- ✅ No blocking or timeouts

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Vertex AI Search not configured | High | Graceful fallback, log warning, proceed without memories |
| IAM permissions missing | High | Document required roles in setup guide |
| Search returns irrelevant results | Medium | Start with top 5, tune later based on feedback |
| Prompt injection too large | Low | Cap at 5 memories, ~750 tokens max |
| Latency too high | Medium | Monitor logs, add caching if needed (Phase 6) |

---

## Post-Implementation

After Phase 3C is complete and tested:

1. **Commit & Push** to dev branch
2. **Update** PHASE_3C_SETUP.md with results
3. **Document** any Vertex AI Search setup issues
4. **Merge** dev → main (Phase 3 complete!)
5. **Next:** Phase 4 (React Frontend)

---

## Notes for Implementation

1. **Start simple:** Get basic retrieval working first, optimize later
2. **Log everything:** Memory queries, result counts, injection success
3. **Test thoroughly:** Phase 3C is user-facing, must be reliable
4. **Handle failures gracefully:** Never break chat if memory retrieval fails
5. **Document clearly:** Future developers need to understand memory flow

**Estimated Implementation Time:** 2-3 hours
- 30 min: vertex_search.py completion
- 45 min: memory_retrieval.py creation
- 30 min: chat.py integration
- 30 min: admin endpoints
- 30 min: testing & validation
- 15 min: documentation updates
