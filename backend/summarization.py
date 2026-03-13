"""Session summarization with parallel LLM calls for event and entity extraction."""
import asyncio
from datetime import datetime, timezone
from typing import Tuple
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage
from models import Session, EventMemory, EntityMemory, FirestoreCollections
from config import GCP_PROJECT_ID, GCP_LOCATION, ASSISTANT_NAME
import logging

logger = logging.getLogger(__name__)

# Use Vertex AI Gemini for summarization (uses Google Cloud credits)
SUMMARIZATION_MODEL = "gemini-2.5-flash"


def extract_event_memory(session: Session) -> str:
    """
    Extract event-based memory from session.
    Returns 3-7 bullet points of concrete events, actions, and outcomes.
    """
    # Build conversation text
    conversation = "\n".join([
        f"{msg.role.upper()}: {msg.content}"
        for msg in session.messages
    ])
    
    # Build tool actions text
    tool_actions = "\n".join([
        f"- {tc.tool_name}: {tc.parameters} → {tc.result}"
        for tc in session.tool_calls
    ]) if session.tool_calls else "No tool actions taken."
    
    # Prepare prompt
    system_prompt = f"""Extract only concrete events, actions, and outcomes from this conversation.

Include:
- Things the user asked for
- Actions {ASSISTANT_NAME} performed
- Meetings discussed
- Emails sent/drafted
- Decisions made
- Calendar events created/modified

Write as 3-7 bullet points maximum. Be specific — include names, dates, and outcomes where available.
Do NOT include preferences, personality observations, or general information about entities.

Format: Plain bullet points starting with "- "
"""
    
    user_message = f"""Conversation:
{conversation}

Tool Actions:
{tool_actions}

Extract event-based memories from above."""
    
    try:
        # Use sync LLM call
        llm = ChatVertexAI(
            model=SUMMARIZATION_MODEL,
            project=GCP_PROJECT_ID,
            location=GCP_LOCATION,
            temperature=0.0,  # Deterministic extraction
            max_retries=6,  # Retry with exponential backoff for rate limits
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # If response is empty or too short, return a fallback
        if len(content) < 20:
            return f"- User had a conversation with {ASSISTANT_NAME} on {session.created_at.strftime('%Y-%m-%d')}"
        
        return content
    
    except Exception as e:
        logger.error(f"Event memory extraction failed: {e}")
        return f"- User had a conversation with {ASSISTANT_NAME} on {session.created_at.strftime('%Y-%m-%d')}"


def extract_entity_memory(session: Session) -> str:
    """
    Extract entity-based memory from session.
    Returns 3-7 bullet points about people, companies, and topics mentioned.
    """
    # Build conversation text
    conversation = "\n".join([
        f"{msg.role.upper()}: {msg.content}"
        for msg in session.messages
    ])
    
    # Prepare prompt
    system_prompt = """Extract only factual information about people, companies, or recurring topics mentioned in this conversation.

Include:
- People mentioned (roles, relationships, contact info)
- Companies or organizations
- Projects or recurring themes
- Important context about entities

Write as 3-7 bullet points maximum.
Do NOT include events or what happened — only who/what things are and their attributes.

Format: Plain bullet points starting with "- "
"""
    
    user_message = f"""Conversation:
{conversation}

Extract entity-based information about people, companies, and topics mentioned."""
    
    try:
        # Use async LLM call
        llm = ChatVertexAI(
            model=SUMMARIZATION_MODEL,
            project=GCP_PROJECT_ID,
            location=GCP_LOCATION,
            temperature=0.0,  # Deterministic extraction
            max_retries=6,  # Retry with exponential backoff for rate limits
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # If response is empty or too short, return fallback
        if len(content) < 20:
            return f"- User interacts with {ASSISTANT_NAME} for calendar and email management"
        
        return content
    
    except Exception as e:
        logger.error(f"Entity memory extraction failed: {e}")
        return f"- User interacts with {ASSISTANT_NAME} for calendar and email management"


def summarize_session(user_id: str, session_id: str) -> None:
    """
    Main summarization orchestration function.
    
    This function:
    1. Fetches the full session from Firestore
    2. Runs 2 LLM calls in parallel (event + entity extraction)
    3. Writes both memories to Firestore
    4. Pushes both memories to Vertex AI Search
    5. Updates session status to 'summarized'
    
    Designed to run as FastAPI BackgroundTask (non-blocking).
    """
    try:
        logger.info(f"Starting summarization for session {session_id}")
        
        # Initialize Firestore client
        fs = FirestoreCollections()
        
        # Fetch session from Firestore
        session = fs.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return
        
        # Skip if session has fewer than 2 messages (nothing to summarize)
        if len(session.messages) < 2:
            logger.info(f"Session {session_id} too short to summarize")
            return
        
        # Run both extractions in parallel using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            event_future = executor.submit(extract_event_memory, session)
            entity_future = executor.submit(extract_entity_memory, session)
            event_content = event_future.result()
            entity_content = entity_future.result()
        
        logger.info(f"Extraction complete for session {session_id}")
        
        # Create EventMemory document
        event_memory = EventMemory(
            user_id=user_id,
            session_id=session_id,
            content=event_content,
            is_update=False,
            supersedes_memory_id=None
        )
        
        # Create EntityMemory document
        entity_memory = EntityMemory(
            user_id=user_id,
            session_id=session_id,
            content=entity_content,
            is_update=False,
            supersedes_memory_id=None
        )
        
        # Write to Firestore
        event_memory_id = fs.create_event_memory(event_memory)
        entity_memory_id = fs.create_entity_memory(entity_memory)
        
        logger.info(f"Memories created: event={event_memory_id}, entity={entity_memory_id}")
        
        # Push to Vertex AI Search
        # Import here to avoid circular dependency
        from vertex_search import push_memory_to_vertex
        
        try:
            event_vertex_id = push_memory_to_vertex(
                memory_id=event_memory_id,
                content=event_content,
                user_id=user_id,
                memory_type="event",
                created_at=event_memory.created_at
            )
            
            entity_vertex_id = push_memory_to_vertex(
                memory_id=entity_memory_id,
                content=entity_content,
                user_id=user_id,
                memory_type="entity",
                created_at=entity_memory.created_at
            )
            
            # Update memory documents with Vertex IDs
            event_memory.vertex_doc_id = event_vertex_id
            entity_memory.vertex_doc_id = entity_vertex_id
            
            # Re-save with Vertex IDs
            fs.create_event_memory(event_memory)
            fs.create_entity_memory(entity_memory)
            
            logger.info(f"Pushed to Vertex AI Search: event={event_vertex_id}, entity={entity_vertex_id}")
        
        except Exception as e:
            logger.warning(f"Vertex AI Search push failed (continuing anyway): {e}")
            # Don't fail the entire summarization if Vertex push fails
        
        # Update session status
        fs.update_session_status(
            session_id=session_id,
            status="summarized",
            summary_event_id=event_memory_id,
            summary_entity_id=entity_memory_id
        )
        
        logger.info(f"Session {session_id} marked as summarized")
    
    except Exception as e:
        logger.error(f"Summarization failed for session {session_id}: {e}", exc_info=True)


def summarize_session_sync(user_id: str, session_id: str) -> None:
    """
    Alias for summarize_session for backwards compatibility.
    Function is now fully synchronous and can be called directly.
    """
    summarize_session(user_id, session_id)

