"""Memory retrieval orchestration with fallback logic for Phase 3C."""
from typing import Dict, List
import logging
from vertex_search import search_memories
from config import (
    MEMORY_RECENCY_DAYS_DEFAULT,
    MEMORY_RECENCY_DAYS_FALLBACK,
    MEMORY_MAX_RESULTS,
    MEMORY_MIN_RESULTS_THRESHOLD
)

logger = logging.getLogger(__name__)


def retrieve_memories_for_message(
    user_message: str,
    user_id: str
) -> Dict[str, any]:
    """
    Retrieve relevant memories with automatic fallback.
    
    Queries Vertex AI Search with 30-day recency window.
    If results < 3, automatically expands to 90-day window.
    
    Args:
        user_message: The user's chat message (used as search query)
        user_id: User ID to filter memories
    
    Returns:
        {
            "event_memories": [str],  # List of event bullet points
            "entity_memories": [str], # List of entity bullet points
            "total_count": int,
            "recency_window_days": int  # 30 or 90
        }
    """
    logger.info(f"Retrieving memories for user {user_id} with query: {user_message[:50]}...")
    
    # Initial query with 30-day window
    results = search_memories(
        query=user_message,
        user_id=user_id,
        max_results=MEMORY_MAX_RESULTS,
        recency_days=MEMORY_RECENCY_DAYS_DEFAULT
    )
    
    recency_window = MEMORY_RECENCY_DAYS_DEFAULT
    
    # If too few results, expand to 90-day window
    if len(results) < MEMORY_MIN_RESULTS_THRESHOLD:
        logger.info(f"Only {len(results)} results with {MEMORY_RECENCY_DAYS_DEFAULT}-day window, expanding to {MEMORY_RECENCY_DAYS_FALLBACK} days")
        
        results = search_memories(
            query=user_message,
            user_id=user_id,
            max_results=MEMORY_MAX_RESULTS,
            recency_days=MEMORY_RECENCY_DAYS_FALLBACK
        )
        
        recency_window = MEMORY_RECENCY_DAYS_FALLBACK
    
    # Filter results by recency window (post-search filtering)
    from datetime import datetime, timedelta, timezone
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=recency_window)
    
    filtered_results = []
    for result in results:
        created_at_str = result.get("created_at")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if created_at >= cutoff_date:
                    filtered_results.append(result)
            except:
                # If date parsing fails, include the result anyway
                filtered_results.append(result)
        else:
            filtered_results.append(result)
    
    # Separate filtered results by type
    event_memories = []
    entity_memories = []
    
    for result in filtered_results:
        content = result.get("content", "")
        memory_type = result.get("type", "")
        
        if memory_type == "event":
            event_memories.append(content)
        elif memory_type == "entity":
            entity_memories.append(content)
    
    total_count = len(event_memories) + len(entity_memories)
    
    logger.info(f"Retrieved {total_count} memories ({len(event_memories)} events, {len(entity_memories)} entities) with {recency_window}-day window")
    
    return {
        "event_memories": event_memories,
        "entity_memories": entity_memories,
        "total_count": total_count,
        "recency_window_days": recency_window
    }


def format_memory_injection(
    event_memories: List[str],
    entity_memories: List[str]
) -> str:
    """
    Format memories into system prompt injection block.
    
    Args:
        event_memories: List of event memory contents (bullet points)
        entity_memories: List of entity memory contents (bullet points)
    
    Returns:
        Formatted string ready for prompt injection.
        Returns empty string if both lists are empty.
    """
    # If no memories at all, return empty string
    if not event_memories and not entity_memories:
        return ""
    
    parts = ["## What you remember about this user\n"]
    
    # Add event memories section
    parts.append("### Recent Events")
    if event_memories:
        for event_content in event_memories:
            # Content is already in bullet point format from summarization
            parts.append(event_content)
    else:
        parts.append("(No recent events recorded)")
    
    parts.append("")  # Blank line between sections
    
    # Add entity memories section
    parts.append("### People and Entities")
    if entity_memories:
        for entity_content in entity_memories:
            # Content is already in bullet point format from summarization
            parts.append(entity_content)
    else:
        parts.append("(No entities recorded)")
    
    return "\n".join(parts)
