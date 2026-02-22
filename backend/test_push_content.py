"""Test pushing a new memory to Vertex with content."""
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import our function
from vertex_search import push_memory_to_vertex

# Create a test memory
memory_id = str(uuid.uuid4())
content = "This is a test memory content to verify that content field is being stored correctly in Vertex AI Search."
user_id = "dev_user_1"
memory_type = "event"
created_at = datetime.now(timezone.utc)

print(f"Pushing test memory: {memory_id}")
print(f"Content: {content}\n")

try:
    vertex_doc_id = push_memory_to_vertex(
        memory_id=memory_id,
        content=content,
        user_id=user_id,
        memory_type=memory_type,
        created_at=created_at
    )
    print(f"✅ Successfully pushed to Vertex with ID: {vertex_doc_id}")
    print(f"\nNow checking if content was stored...")
    
    # Wait a moment for the write to complete
    import time
    time.sleep(2)
    
    # Check the document
    from google.cloud import discoveryengine_v1 as discoveryengine
    
    client = discoveryengine.DocumentServiceClient()
    doc_path = client.document_path(
        project=os.getenv("FIREBASE_PROJECT_ID"),
        location=os.getenv("VERTEX_LOCATION", "global"),
        data_store=os.getenv("VERTEX_DATASTORE_ID"),
        branch="default_branch",
        document=vertex_doc_id
    )
    
    doc = client.get_document(name=doc_path)
    
    print("\n=== Retrieved Document ===")
    print(f"Document ID: {doc.name}")
    print(f"Has content field: {doc.content is not None and doc.content.raw_bytes}")
    if doc.content and doc.content.raw_bytes:
        retrieved_content = doc.content.raw_bytes.decode('utf-8')
        print(f"Content length: {len(retrieved_content)}")
        print(f"Content: {retrieved_content[:100]}...")
        print(f"\n✅ Content IS being stored!")
    else:
        print(f"❌ Content field is empty or missing")
        print(f"Document fields: {doc}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
