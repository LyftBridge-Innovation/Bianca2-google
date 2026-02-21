"""Vertex AI Search integration for memory indexing and retrieval."""
from datetime import datetime
from typing import Optional
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.protobuf.json_format import ParseDict
from config import FIREBASE_PROJECT_ID
import os
import logging

logger = logging.getLogger(__name__)

# Vertex AI Search configuration (loaded from environment)
VERTEX_DATASTORE_ID = os.getenv("VERTEX_DATASTORE_ID")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "global")
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", FIREBASE_PROJECT_ID)


async def push_memory_to_vertex(
    memory_id: str,
    content: str,
    user_id: str,
    memory_type: str,
    created_at: datetime
) -> str:
    """
    Push a memory document to Vertex AI Search.
    
    Args:
        memory_id: Unique memory identifier (from Firestore)
        content: The memory text content (bullet points)
        user_id: User this memory belongs to
        memory_type: "event" or "entity"
        created_at: Timestamp when memory was created
    
    Returns:
        Vertex AI Search document ID (usually same as memory_id)
    
    Raises:
        Exception if Vertex AI Search is not configured or push fails
    """
    # Check if Vertex AI Search is configured
    if not VERTEX_DATASTORE_ID:
        logger.warning("VERTEX_DATASTORE_ID not configured, skipping Vertex AI Search push")
        raise Exception("Vertex AI Search not configured")
    
    try:
        # Create the document client
        client = discoveryengine.DocumentServiceClient()
        
        # Build the parent path for the datastore
        parent = client.branch_path(
            project=VERTEX_PROJECT_ID,
            location=VERTEX_LOCATION,
            data_store=VERTEX_DATASTORE_ID,
            branch="default_branch"
        )
        
        # Prepare the document
        document = {
            "id": memory_id,
            "structData": {
                "content": content,
                "user_id": user_id,
                "type": memory_type,
                "created_at": created_at.isoformat(),
                "memory_id": memory_id
            }
        }
        
        # Convert to proto message
        document_proto = discoveryengine.Document(ParseDict(document, discoveryengine.Document()))
        
        # Create the request
        request = discoveryengine.CreateDocumentRequest(
            parent=parent,
            document=document_proto,
            document_id=memory_id
        )
        
        # Push the document
        response = client.create_document(request=request)
        
        logger.info(f"Pushed memory {memory_id} to Vertex AI Search: {response.name}")
        
        return memory_id
    
    except Exception as e:
        logger.error(f"Failed to push memory {memory_id} to Vertex AI Search: {e}")
        raise


async def search_memories(
    query: str,
    user_id: str,
    max_results: int = 5,
    recency_days: int = 30
) -> list:
    """
    Search for relevant memories in Vertex AI Search.
    
    Args:
        query: User's message text (used as search query)
        user_id: Filter results to this user only
        max_results: Maximum number of results to return
        recency_days: Only return memories from last N days
    
    Returns:
        List of memory documents with content and metadata
    
    This function is used in Phase 3C for memory retrieval.
    """
    # Check if Vertex AI Search is configured
    if not VERTEX_DATASTORE_ID:
        logger.warning("VERTEX_DATASTORE_ID not configured, returning empty results")
        return []
    
    try:
        # Create the search client
        client = discoveryengine.SearchServiceClient()
        
        # Build the serving config path
        serving_config = client.serving_config_path(
            project=VERTEX_PROJECT_ID,
            location=VERTEX_LOCATION,
            data_store=VERTEX_DATASTORE_ID,
            serving_config="default_config"
        )
        
        # Build the search request with filters
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=max_results,
            # Filter by user_id (Vertex AI Search filter syntax)
            filter=f'user_id: ANY("{user_id}")',
            # TODO: Add recency filter once we implement date filtering
        )
        
        # Execute search
        response = client.search(request=request)
        
        # Extract results
        results = []
        for result in response.results:
            doc_data = result.document.struct_data
            results.append({
                "memory_id": doc_data.get("memory_id"),
                "content": doc_data.get("content"),
                "type": doc_data.get("type"),
                "created_at": doc_data.get("created_at")
            })
        
        logger.info(f"Found {len(results)} memories for user {user_id} with query: {query[:50]}...")
        
        return results
    
    except Exception as e:
        logger.error(f"Vertex AI Search query failed: {e}")
        return []

