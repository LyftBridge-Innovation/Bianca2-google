"""Firestore data models and collection managers for Phase 3A."""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from firestore_client import get_firestore_client
from google.cloud import firestore
import uuid


# ── Pydantic Models ───────────────────────────────────────────────────────────


class AgentSettings(BaseModel):
    """Per-user agent configuration — embedded in the User document."""
    ai_name: str = "Bianca"
    ai_role: str = "AI Chief of Staff"
    ai_voice: str = "Aoede"
    primary_language: str = "English"
    secondary_language: str = ""
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.7
    custom_prompt: str = ""
    slides_template_id: str = ""
    docs_template_id: str = ""
    sheets_template_id: str = ""
    voice_prompt: str = ""
    voice_greeting: str = ""
    email_polling_interval: int = 15
    email_polling_days: str = "weekdays"
    # BYOK — never falls back to shared env vars
    google_api_key: str = ""
    anthropic_api_key: str = ""


class User(BaseModel):
    """User profile document."""
    user_id: str
    email: str
    full_name: str = ""
    job_title: str = ""
    company: str = ""
    timezone: str = "UTC"
    google_refresh_token: str = ""
    assistant_name: str = "Bianca"
    enabled_skills: list[str] = Field(
        default_factory=list,
        description="Skill names enabled for this user. Empty = all skills."
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Agent configuration (per-user, BYOK) ──────────────────────────────────
    agent_settings: AgentSettings = Field(default_factory=AgentSettings)
    onboarding_completed: bool = False
    onboarding_step: int = 0  # 0=not started, 1-4=steps in progress, 5=done

    # ── Email Agent ────────────────────────────────────────────────────────────
    email_agent_enabled: bool = False
    email_agent_label_name: str = ""     # Gmail label name user configures
    email_agent_label_id: str = ""       # Resolved Gmail label ID
    email_agent_history_id: str = ""     # Last processed Gmail historyId
    email_agent_watch_expiry: int = 0    # Unix timestamp in ms (watch expires after 7 days)
    email_agent_replied_count: int = 0   # Lifetime count of auto-replies sent


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


class Task(BaseModel):
    """Background task document for async operations."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: Optional[str] = None

    # Task definition
    task_type: str  # "create_doc", "send_email", "create_slides", "create_sheet"
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Status tracking
    status: str = "pending"  # pending, running, completed, failed
    progress: int = 0  # 0-100 percentage
    progress_message: str = ""

    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Cloud Tasks metadata (for production)
    cloud_task_name: Optional[str] = None


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

    # ── User Skills ────────────────────────────────────────────────────────

    def create_user_skill(self, user_id: str, skill_data: Dict[str, Any]) -> None:
        """Create a skill document under a user's skills subcollection."""
        self.db.collection('users').document(user_id)\
            .collection('skills').document(skill_data['skill_id']).set(skill_data)

    def list_user_skills(self, user_id: str) -> List[Dict[str, Any]]:
        """List all skills for a user, most recent first."""
        docs = self.db.collection('users').document(user_id)\
            .collection('skills').stream()
        skills = [doc.to_dict() for doc in docs]
        skills.sort(key=lambda s: s.get('created_at', ''), reverse=True)
        return skills

    def get_user_skills_for_matching(self, user_id: str) -> List[Dict[str, str]]:
        """Get skills with title + content for the skill matcher."""
        docs = self.db.collection('users').document(user_id)\
            .collection('skills').stream()
        return [
            {
                'skill_id': doc.id,
                'title': doc.to_dict().get('title', ''),
                'content': doc.to_dict().get('content', ''),
            }
            for doc in docs
        ]

    def delete_user_skill(self, user_id: str, skill_id: str) -> bool:
        """Delete a skill. Returns True if it existed."""
        ref = self.db.collection('users').document(user_id)\
            .collection('skills').document(skill_id)
        doc = ref.get()
        if doc.exists:
            ref.delete()
            return True
        return False

    # ── Public Skills (Marketplace) ────────────────────────────────────────

    def create_public_skill(self, skill_data: Dict[str, Any]) -> str:
        """Publish a skill to the marketplace. Returns skill_id."""
        doc_ref = self.db.collection('public_skills').document()
        skill_data['skill_id'] = doc_ref.id
        skill_data['install_count'] = 0
        doc_ref.set(skill_data)
        return doc_ref.id

    def list_public_skills(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all marketplace skills, sorted by install_count desc."""
        docs = self.db.collection('public_skills')\
            .order_by('install_count', direction=firestore.Query.DESCENDING)\
            .limit(limit).stream()
        return [doc.to_dict() for doc in docs]

    def get_public_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a single marketplace skill by ID."""
        doc = self.db.collection('public_skills').document(skill_id).get()
        return doc.to_dict() if doc.exists else None

    def delete_public_skill(self, skill_id: str) -> bool:
        """Delete a marketplace skill (author only). Returns True if existed."""
        doc_ref = self.db.collection('public_skills').document(skill_id)
        if doc_ref.get().exists:
            doc_ref.delete()
            return True
        return False

    def increment_install_count(self, skill_id: str) -> None:
        """Increment install counter for a marketplace skill."""
        doc_ref = self.db.collection('public_skills').document(skill_id)
        doc_ref.update({'install_count': firestore.Increment(1)})

    # ── Tasks (Background Job Queue) ───────────────────────────────────────

    def create_task(self, task: 'Task') -> str:
        """Create a new task and return its ID."""
        self.db.collection('tasks').document(task.task_id).set(task.model_dump())
        return task.task_id

    def get_task(self, task_id: str) -> Optional['Task']:
        """Get a task by ID."""
        doc = self.db.collection('tasks').document(task_id).get()
        if doc.exists:
            return Task(**doc.to_dict())
        return None

    def update_task(self, task_id: str, **updates) -> None:
        """Update specific fields on a task."""
        self.db.collection('tasks').document(task_id).update(updates)

    def list_tasks(self, user_id: str, status: Optional[str] = None, limit: int = 50) -> List['Task']:
        """List tasks for a user, optionally filtered by status."""
        query = self.db.collection('tasks').where('user_id', '==', user_id)
        if status:
            query = query.where('status', '==', status)
        docs = query.limit(limit).stream()
        tasks = [Task(**doc.to_dict()) for doc in docs]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def delete_task(self, task_id: str) -> bool:
        """Delete a task. Returns True if it existed."""
        doc_ref = self.db.collection('tasks').document(task_id)
        if doc_ref.get().exists:
            doc_ref.delete()
            return True
        return False

    # ── Per-user Agent Settings ────────────────────────────────────────────────

    def save_user_agent_settings(self, user_id: str, settings: 'AgentSettings') -> None:
        """Write agent_settings + onboarding fields into the user document."""
        self.db.collection('users').document(user_id).set(
            {
                'agent_settings': settings.model_dump(),
                'updated_at': datetime.now(timezone.utc),
            },
            merge=True,
        )

    def update_onboarding_state(self, user_id: str, step: int, completed: bool = False) -> None:
        """Update the onboarding step / completion flag on the user document."""
        self.db.collection('users').document(user_id).set(
            {
                'onboarding_step': step,
                'onboarding_completed': completed,
                'updated_at': datetime.now(timezone.utc),
            },
            merge=True,
        )

    # ── Per-user Knowledge Subcollection ──────────────────────────────────────
    # Subcollection path: users/{user_id}/knowledge/{section_id}
    # Valid section_ids: persona, education_text, expertise, company,
    #                    education_structured, resume

    def _knowledge_ref(self, user_id: str, section_id: str):
        return (
            self.db.collection('users').document(user_id)
            .collection('knowledge').document(section_id)
        )

    def save_user_knowledge_section(self, user_id: str, section_id: str, content: str) -> None:
        """Save a text knowledge section for a user."""
        self._knowledge_ref(user_id, section_id).set(
            {'content': content, 'updated_at': datetime.now(timezone.utc)}
        )

    def get_user_knowledge_section(self, user_id: str, section_id: str) -> str:
        """Get a text knowledge section. Returns '' if not found."""
        doc = self._knowledge_ref(user_id, section_id).get()
        if doc.exists:
            return doc.to_dict().get('content', '')
        return ''

    def save_user_education(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save structured education data (degrees + courses)."""
        self._knowledge_ref(user_id, 'education_structured').set(
            {**data, 'updated_at': datetime.now(timezone.utc)}
        )

    def get_user_education(self, user_id: str) -> Dict[str, Any]:
        """Get structured education data. Returns empty structure if not found."""
        doc = self._knowledge_ref(user_id, 'education_structured').get()
        if doc.exists:
            d = doc.to_dict()
            return {'degrees': d.get('degrees', []), 'courses': d.get('courses', [])}
        return {'degrees': [], 'courses': []}

    def save_user_resume(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save resume / work experience data."""
        self._knowledge_ref(user_id, 'resume').set(
            {**data, 'updated_at': datetime.now(timezone.utc)}
        )

    def get_user_resume(self, user_id: str) -> Dict[str, Any]:
        """Get resume data. Returns empty structure if not found."""
        doc = self._knowledge_ref(user_id, 'resume').get()
        if doc.exists:
            d = doc.to_dict()
            return {'experience': d.get('experience', [])}
        return {'experience': []}

    def get_all_user_knowledge_sections(self, user_id: str) -> Dict[str, str]:
        """Return all text sections in one call. Returns {section_id: content}."""
        docs = (
            self.db.collection('users').document(user_id)
            .collection('knowledge').stream()
        )
        result: Dict[str, str] = {}
        for doc in docs:
            d = doc.to_dict()
            result[doc.id] = d.get('content', '')
        return result

    # ── Per-user Values Subcollection ─────────────────────────────────────────
    # Subcollection path: users/{user_id}/values/config

    def _values_ref(self, user_id: str):
        return (
            self.db.collection('users').document(user_id)
            .collection('values').document('config')
        )

    def save_user_values(self, user_id: str, values: List[Dict[str, Any]]) -> None:
        """Save a user's values list."""
        self._values_ref(user_id).set(
            {'items': values, 'updated_at': datetime.now(timezone.utc)}
        )

    def get_user_values(self, user_id: str) -> List[Dict[str, Any]]:
        """Get a user's values list. Returns [] if not set (caller should use defaults)."""
        doc = self._values_ref(user_id).get()
        if doc.exists:
            return doc.to_dict().get('items', [])
        return []

    # ── Full user data deletion ────────────────────────────────────────────────

    def _delete_subcollection(self, parent_ref, subcollection_name: str) -> int:
        """Delete all documents in a subcollection. Returns count deleted."""
        count = 0
        for doc in parent_ref.collection(subcollection_name).stream():
            doc.reference.delete()
            count += 1
        return count

    def _delete_collection_where(self, collection_name: str, field: str, value: str) -> int:
        """
        Delete all documents in a top-level collection where field == value.
        Runs in batches of 400 to stay under Firestore's 500-op batch limit.
        Returns total count deleted.
        """
        count = 0
        while True:
            docs = (
                self.db.collection(collection_name)
                .where(field, '==', value)
                .limit(400)
                .stream()
            )
            batch = self.db.batch()
            batch_count = 0
            for doc in docs:
                batch.delete(doc.reference)
                batch_count += 1
            if batch_count == 0:
                break
            batch.commit()
            count += batch_count
        return count

    def delete_user_all_data(self, user_id: str) -> Dict[str, int]:
        """
        Permanently delete a user and ALL associated data from Firestore.

        Removes:
          - users/{user_id}/knowledge/*   (knowledge subcollection)
          - users/{user_id}/values/*      (values subcollection)
          - users/{user_id}/skills/*      (skills subcollection)
          - users/{user_id}               (the user document)
          - sessions          where user_id == user_id
          - event_memories    where user_id == user_id
          - entity_memories   where user_id == user_id
          - tasks             where user_id == user_id
          - tool_action_log   where user_id == user_id

        Returns a dict of { collection_name: count_deleted }.
        This operation is IRREVERSIBLE.
        """
        user_ref = self.db.collection('users').document(user_id)
        deleted: Dict[str, int] = {}

        # 1. Subcollections under the user document
        deleted['knowledge'] = self._delete_subcollection(user_ref, 'knowledge')
        deleted['values']    = self._delete_subcollection(user_ref, 'values')
        deleted['skills']    = self._delete_subcollection(user_ref, 'skills')

        # 2. The user document itself
        user_ref.delete()
        deleted['user'] = 1

        # 3. Top-level collections keyed by user_id
        for col in ('sessions', 'event_memories', 'entity_memories', 'tasks', 'tool_action_log'):
            deleted[col] = self._delete_collection_where(col, 'user_id', user_id)

        return deleted
