"""Admin endpoints for Phase 3A setup and testing."""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
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


# ── Config migration ──────────────────────────────────────────────────────────

@router.post("/migrate-config/{user_id}")
def migrate_disk_config_to_firestore(user_id: str):
    """
    One-time migration: copy the current global disk config (settings.json,
    knowledge/ files, values_override.json, education.json, resume.json) into
    Firestore for the given user.

    After this runs, the user will see their existing config in Neural Config
    and will have onboarding_completed=True (skipping the wizard).

    Safe to run multiple times — it overwrites Firestore with the latest disk
    state on each call.
    """
    import json
    from pathlib import Path
    from models import AgentSettings

    user = fs.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    _knowledge_dir = Path(__file__).parent.parent / "knowledge"
    migrated: dict = {}

    # ── Agent settings ────────────────────────────────────────────────────────
    settings_path = _knowledge_dir / "settings.json"
    disk_settings: dict = {}
    if settings_path.exists():
        try:
            disk_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Merge disk settings onto the model defaults, then onto what's already in Firestore
    merged = AgentSettings().model_dump()
    merged.update(disk_settings)
    # Preserve any keys already in the user's Firestore settings (e.g. api keys set manually)
    existing = user.agent_settings.model_dump()
    for key in ("google_api_key", "anthropic_api_key"):
        if existing.get(key, ""):
            merged[key] = existing[key]
    fs.save_user_agent_settings(user_id, AgentSettings(**merged))
    migrated["settings"] = True

    # ── Knowledge text sections ───────────────────────────────────────────────
    section_map = {
        "01_persona":   "persona",
        "02_education": "education_text",
        "03_expertise": "expertise",
        "04_company":   "company",
    }
    migrated["knowledge"] = {}
    for dir_name, section_id in section_map.items():
        dir_path = _knowledge_dir / dir_name
        if not dir_path.exists():
            continue
        parts = []
        for fp in sorted(dir_path.iterdir()):
            if fp.suffix in (".txt", ".md") and fp.is_file():
                content = fp.read_text(encoding="utf-8").strip()
                if content:
                    parts.append(content)
        if parts:
            fs.save_user_knowledge_section(user_id, section_id, "\n\n".join(parts))
            migrated["knowledge"][section_id] = True

    # ── Education structured ──────────────────────────────────────────────────
    edu_path = _knowledge_dir / "education.json"
    if edu_path.exists():
        try:
            edu_data = json.loads(edu_path.read_text(encoding="utf-8"))
            fs.save_user_education(user_id, edu_data)
            migrated["education"] = True
        except Exception:
            migrated["education"] = False

    # ── Resume ────────────────────────────────────────────────────────────────
    resume_path = _knowledge_dir / "resume.json"
    if resume_path.exists():
        try:
            resume_data = json.loads(resume_path.read_text(encoding="utf-8"))
            fs.save_user_resume(user_id, resume_data)
            migrated["resume"] = True
        except Exception:
            migrated["resume"] = False

    # ── Values ────────────────────────────────────────────────────────────────
    values_path = _knowledge_dir / "values_override.json"
    if values_path.exists():
        try:
            values_data = json.loads(values_path.read_text(encoding="utf-8"))
            if values_data:
                fs.save_user_values(user_id, values_data)
                migrated["values"] = True
        except Exception:
            migrated["values"] = False

    # ── Mark onboarding complete ──────────────────────────────────────────────
    fs.update_onboarding_state(user_id, step=5, completed=True)
    migrated["onboarding_completed"] = True

    return {
        "ok": True,
        "user_id": user_id,
        "migrated": migrated,
        "message": "Disk config migrated to Firestore. Onboarding marked complete.",
    }


# ── User deletion ──────────────────────────────────────────────────────────────

@router.delete("/user/{user_id}")
def delete_user(
    user_id: str,
    confirm: bool = Query(
        False,
        description="Must be true to execute the deletion. Prevents accidental calls.",
    ),
):
    """
    Permanently delete a user and ALL their data from Firestore.

    Deletes:
      - The user document (users/{user_id})
      - All subcollections: knowledge, values, skills
      - All sessions, memories, tasks, and tool_action_log entries for this user

    This is IRREVERSIBLE. You must pass ?confirm=true to execute.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail=(
                "Deletion requires ?confirm=true. "
                "This action permanently removes the user and all associated data."
            ),
        )

    user = fs.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")

    # Snapshot identity before deleting
    user_email = user.email
    user_name  = user.full_name

    deleted = fs.delete_user_all_data(user_id)

    return {
        "ok": True,
        "user_id": user_id,
        "email": user_email,
        "name": user_name,
        "deleted": deleted,
        "total_documents_removed": sum(deleted.values()),
        "message": f"User {user_email} and all associated data have been permanently deleted.",
    }

