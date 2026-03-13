"""Admin endpoints for Phase 3A setup and testing."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models import FirestoreCollections, User
import os
from config import TEST_USER_ID, ASSISTANT_NAME
from summarization import summarize_session_sync

router = APIRouter(prefix="/admin", tags=["admin"])
fs = FirestoreCollections()


@router.post("/init-test-user")
def initialize_test_user():
    """
    Initialize the test user in Firestore.
    Run this once before testing Phase 3A.
    """
    try:
        # Check if user already exists
        existing_user = fs.get_user(TEST_USER_ID)
        if existing_user:
            return {
                "status": "already_exists",
                "user_id": TEST_USER_ID,
                "message": "Test user already initialized"
            }
        
        # Create test user
        test_user = User(
            user_id=TEST_USER_ID,
            email="dev@example.com",
            full_name="Test Developer",
            job_title="Software Engineer",
            company="Test Corp",
            timezone="America/Los_Angeles",
            google_refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN", ""),
            assistant_name=ASSISTANT_NAME
        )
        
        fs.create_or_update_user(test_user)
        
        return {
            "status": "created",
            "user_id": TEST_USER_ID,
            "message": "Test user initialized successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize test user: {str(e)}")


@router.get("/user/{user_id}")
def get_user(user_id: str):
    """Get user details."""
    user = fs.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.model_dump()


@router.get("/tool-actions/{user_id}")
def get_user_tool_actions(user_id: str, limit: int = 10):
    """Get recent tool actions for a user."""
    try:
        docs = fs.db.collection('tool_action_log')\
            .where('user_id', '==', user_id)\
            .order_by('timestamp', direction='DESCENDING')\
            .limit(limit)\
            .get()
        
        actions = [doc.to_dict() for doc in docs]
        return {"actions": actions, "count": len(actions)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tool actions: {str(e)}")


# ── Phase 3B Admin Endpoints ──────────────────────────────────────────────────


@router.get("/memory/event/{memory_id}")
def get_event_memory(memory_id: str):
    """Get a specific event memory by ID."""
    try:
        doc = fs.db.collection('event_memories').document(memory_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Event memory not found")
        return doc.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch event memory: {str(e)}")


@router.get("/memory/entity/{memory_id}")
def get_entity_memory(memory_id: str):
    """Get a specific entity memory by ID."""
    try:
        doc = fs.db.collection('entity_memories').document(memory_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Entity memory not found")
        return doc.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch entity memory: {str(e)}")


@router.get("/memories/{user_id}")
def get_user_memories(user_id: str, memory_type: str = None, limit: int = 10):
    """Get all memories for a user, optionally filtered by type."""
    try:
        results = {"event_memories": [], "entity_memories": []}
        
        if not memory_type or memory_type == "event":
            event_docs = fs.db.collection('event_memories')\
                .where('user_id', '==', user_id)\
                .order_by('created_at', direction='DESCENDING')\
                .limit(limit)\
                .get()
            results["event_memories"] = [doc.to_dict() for doc in event_docs]
        
        if not memory_type or memory_type == "entity":
            entity_docs = fs.db.collection('entity_memories')\
                .where('user_id', '==', user_id)\
                .order_by('created_at', direction='DESCENDING')\
                .limit(limit)\
                .get()
            results["entity_memories"] = [doc.to_dict() for doc in entity_docs]
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch memories: {str(e)}")


@router.post("/re-summarize/{session_id}")
async def re_summarize_session(session_id: str, background_tasks: BackgroundTasks):
    """
    Manually trigger re-summarization of a session.
    Useful for testing immutability (creates new memories with is_update=True).
    """
    try:
        # Get the session
        session = fs.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Trigger summarization as background task
        background_tasks.add_task(
            summarize_session_sync,
            user_id=session.user_id,
            session_id=session_id
        )
        
        return {
            "status": "triggered",
            "session_id": session_id,
            "message": "Re-summarization started in background"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger re-summarization: {str(e)}")


@router.post("/test-summarize/{session_id}")
def test_summarize_sync(session_id: str):
    """
    Test endpoint that runs summarization synchronously to see errors.
    NOT for production - blocks the request until completion.
    """
    try:
        session = fs.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Run synchronously to see any errors
        from summarization import summarize_session
        summarize_session(user_id=session.user_id, session_id=session_id)
        
        return {
            "status": "completed",
            "session_id": session_id,
            "message": "Summarization completed successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


# ── Phase 3C Admin Endpoints ──────────────────────────────────────────────────

from pydantic import BaseModel

class MemoryRetrievalRequest(BaseModel):
    query: str
    user_id: str
    recency_days: int = 30


@router.post("/test-memory-retrieval")
def test_memory_retrieval(request: MemoryRetrievalRequest):
    """
    Test memory retrieval without going through chat.
    Useful for debugging Vertex AI Search queries.
    """
    try:
        from memory_retrieval import retrieve_memories_for_message
        
        result = retrieve_memories_for_message(request.query, request.user_id)
        
        return {
            "status": "success",
            "query": request.query,
            "user_id": request.user_id,
            "total_count": result["total_count"],
            "recency_window_days": result["recency_window_days"],
            "event_count": len(result["event_memories"]),
            "entity_count": len(result["entity_memories"]),
            "event_memories": result["event_memories"],
            "entity_memories": result["entity_memories"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory retrieval test failed: {str(e)}")


@router.get("/all-memories/{user_id}")
def get_all_memories(user_id: str, limit: int = 20):
    """
    Get all memories for debugging (bypasses indices).
    Returns both event and entity memories without ordering.
    """
    try:
        # Direct Firestore query without ordering (avoids index requirements)
        event_docs = fs.db.collection('event_memories')\
            .where('user_id', '==', user_id)\
            .limit(limit)\
            .stream()
        
        entity_docs = fs.db.collection('entity_memories')\
            .where('user_id', '==', user_id)\
            .limit(limit)\
            .stream()
        
        event_memories = [doc.to_dict() for doc in event_docs]
        entity_memories = [doc.to_dict() for doc in entity_docs]
        
        return {
            "user_id": user_id,
            "event_memories": event_memories,
            "entity_memories": entity_memories,
            "total_count": len(event_memories) + len(entity_memories)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch all memories: {str(e)}")

