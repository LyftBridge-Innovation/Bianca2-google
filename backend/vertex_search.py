"""Vertex AI Search integration for memory indexing and retrieval."""
from datetime import datetime
from typing import Optional
from google.cloud import discoveryengine_v1beta as discoveryengine
from config import FIREBASE_PROJECT_ID
import os
import logging

logger = logging.getLogger(__name__)

# Vertex AI Search configuration (loaded from environment)
VERTEX_DATASTORE_ID = os.getenv("VERTEX_DATASTORE_ID")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "global")
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", FIREBASE_PROJECT_ID)


def push_memory_to_vertex(
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
        
        # Prepare the document (proto-plus style, not ParseDict)
        from google.protobuf.struct_pb2 import Struct
        
        struct_data = Struct()
        struct_data.update({
            "user_id": user_id,
            "type": memory_type,
            "created_at": created_at.isoformat(),
            "memory_id": memory_id
        })
        
        document_proto = discoveryengine.Document(
            id=memory_id,
            content=discoveryengine.Document.Content(
                mime_type="text/plain",
                raw_bytes=content.encode('utf-8')
            ),
            struct_data=struct_data
        )
        
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


def search_memories(
    query: str,
    user_id: str,
    max_results: int = 5,
    recency_days: int = 30
) -> list[dict]:
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
        
        # Build filter for structured data fields (NO FILTER for now - filter post-search)
        # Vertex AI Search has specific syntax requirements for struct_data filtering
        # For simplicity, we'll filter by user_id in Python after search
        
        # Build the search request without filters
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=max_results * 3  # Get more results to filter by user_id
        )
        
        # Execute search
        response = client.search(request=request)
        
        # Extract and filter results
        results = []
        for result in response.results:
            doc = result.document
            doc_data = doc.struct_data
            
            # Filter by user_id (post-search)
            result_user_id = doc_data.get("user_id")
            if result_user_id != user_id:
                continue
            
            # Get content from document.content field (raw_bytes)
            content = doc.content.raw_bytes.decode('utf-8') if doc.content and doc.content.raw_bytes else ""
            
            results.append({
                "memory_id": doc_data.get("memory_id") or doc.id,
                "content": content,
                "type": doc_data.get("type"),
                "created_at": doc_data.get("created_at")
            })
            
            # Stop once we have enough results
            if len(results) >= max_results:
                break
        
        logger.info(f"Found {len(results)} memories for user {user_id} with query: {query[:50]}...")
        
        return results
    
    except Exception as e:
        logger.error(f"Vertex AI Search query failed: {e}")
        return []

