"""Firestore data models and collection managers for Phase 3A."""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from firestore_client import get_firestore_client
import uuid


# ── Pydantic Models ───────────────────────────────────────────────────────────


class User(BaseModel):
    """User profile document."""
    user_id: str
    email: str
    full_name: str = ""
    job_title: str = ""
    company: str = ""
    timezone: str = "UTC"
    google_refresh_token: str
    assistant_name: str = "Bianca"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(BaseModel):
    """Message object within a session."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolCall(BaseModel):
    """Tool call object within a session."""
    tool_name: str
    parameters: Dict[str, Any]
    result: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Session(BaseModel):
    """Chat session document."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    modality: str = "chat"  # chat, voice, email, sms
    status: str = "active"  # active, summarized
    messages: List[Message] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summarized_at: Optional[datetime] = None
    summary_event_id: Optional[str] = None
    summary_entity_id: Optional[str] = None


class ToolActionLog(BaseModel):
    """Global audit log of tool actions."""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    tool_name: str
    human_readable: str
    parameters: Dict[str, Any]
    result: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modality: str = "chat"


class EventMemory(BaseModel):
    """Event-based memory document."""
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    type: str = "event"
    content: str
    is_update: bool = False
    supersedes_memory_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vertex_doc_id: Optional[str] = None


class EntityMemory(BaseModel):
    """Entity-based memory document."""
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    type: str = "entity"
    content: str
    is_update: bool = False
    supersedes_memory_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vertex_doc_id: Optional[str] = None


# ── Firestore Collection Managers ────────────────────────────────────────────


class FirestoreCollections:
    """Helper class for interacting with Firestore collections."""
    
    def __init__(self):
        self.db = get_firestore_client()
    
    # ── Users ─────────────────────────────────────────────────────────────────
    
    def create_or_update_user(self, user: User) -> None:
        """Create or update a user document."""
        user.updated_at = datetime.now(timezone.utc)
        self.db.collection('users').document(user.user_id).set(user.model_dump())
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user document by ID."""
        doc = self.db.collection('users').document(user_id).get()
        if doc.exists:
            return User(**doc.to_dict())
        return None
    
    # ── Sessions ──────────────────────────────────────────────────────────────
    
    def create_session(self, session: Session) -> str:
        """Create a new session and return its ID."""
        self.db.collection('sessions').document(session.session_id).set(session.model_dump())
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session document by ID."""
        doc = self.db.collection('sessions').document(session_id).get()
        if doc.exists:
            data = doc.to_dict()
            # Convert message and tool_call dicts back to objects
            if 'messages' in data:
                data['messages'] = [Message(**m) for m in data['messages']]
            if 'tool_calls' in data:
                data['tool_calls'] = [ToolCall(**t) for t in data['tool_calls']]
            return Session(**data)
        return None
    
    def append_message(self, session_id: str, message: Message) -> None:
        """Append a message to a session and update last_activity_at."""
        self.db.collection('sessions').document(session_id).update({
            'messages': firestore.ArrayUnion([message.model_dump()]),
            'last_activity_at': datetime.now(timezone.utc)
        })
    
    def append_tool_call(self, session_id: str, tool_call: ToolCall) -> None:
        """Append a tool call to a session."""
        self.db.collection('sessions').document(session_id).update({
            'tool_calls': firestore.ArrayUnion([tool_call.model_dump()])
        })
    
    def update_session_status(self, session_id: str, status: str, 
                             summary_event_id: Optional[str] = None,
                             summary_entity_id: Optional[str] = None) -> None:
        """Update session status and summary references."""
        update_data = {
            'status': status,
            'summarized_at': datetime.now(timezone.utc)
        }
        if summary_event_id:
            update_data['summary_event_id'] = summary_event_id
        if summary_entity_id:
            update_data['summary_entity_id'] = summary_entity_id
        
        self.db.collection('sessions').document(session_id).update(update_data)
    
    def get_active_session_for_user(self, user_id: str) -> Optional[Session]:
        """Get the most recent active session for a user."""
        docs = self.db.collection('sessions')\
            .where('user_id', '==', user_id)\
            .where('status', '==', 'active')\
            .order_by('last_activity_at', direction=firestore.Query.DESCENDING)\
            .limit(1)\
            .get()
        
        if docs:
            data = docs[0].to_dict()
            if 'messages' in data:
                data['messages'] = [Message(**m) for m in data['messages']]
            if 'tool_calls' in data:
                data['tool_calls'] = [ToolCall(**t) for t in data['tool_calls']]
            return Session(**data)
        return None
    
    # ── Tool Action Log ───────────────────────────────────────────────────────
    
    def log_tool_action(self, log: ToolActionLog) -> str:
        """Log a tool action and return its ID."""
        self.db.collection('tool_action_log').document(log.log_id).set(log.model_dump())
        return log.log_id
    
    # ── Event Memories ────────────────────────────────────────────────────────
    
    def create_event_memory(self, memory: EventMemory) -> str:
        """Create an event memory and return its ID."""
        self.db.collection('event_memories').document(memory.memory_id).set(memory.model_dump())
        return memory.memory_id
    
    # ── Entity Memories ───────────────────────────────────────────────────────
    
    def create_entity_memory(self, memory: EntityMemory) -> str:
        """Create an entity memory and return its ID."""
        self.db.collection('entity_memories').document(memory.memory_id).set(memory.model_dump())
        return memory.memory_id
