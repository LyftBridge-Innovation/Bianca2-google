"""Debug script to check Vertex AI Search document structure."""
from google.cloud import discoveryengine_v1beta as discoveryengine
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup
VERTEX_DATASTORE_ID = os.getenv("VERTEX_DATASTORE_ID")
VERTEX_LOCATION = "global"
VERTEX_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

print(f"Using project: {VERTEX_PROJECT_ID}")
print(f"Using datastore: {VERTEX_DATASTORE_ID}")
print()

client = discoveryengine.SearchServiceClient()

serving_config = client.serving_config_path(
    project=VERTEX_PROJECT_ID,
    location=VERTEX_LOCATION,
    data_store=VERTEX_DATASTORE_ID,
    serving_config="default_config"
)

request = discoveryengine.SearchRequest(
    serving_config=serving_config,
    query="Bianca",
    page_size=1
)

response = client.search(request=request)

for result in response.results:
    doc = result.document
    print(f"Document ID: {doc.id}")
    print(f"\n=== Content Field ===")
    print(f"Has content: {bool(doc.content)}")
    if doc.content:
        print(f"  mime_type: {doc.content.mime_type}")
        print(f"  raw_bytes exists: {bool(doc.content.raw_bytes)}")
        if doc.content.raw_bytes:
            print(f"  raw_bytes length: {len(doc.content.raw_bytes)}")
            print(f"  decoded: {doc.content.raw_bytes.decode('utf-8')[:100]}")
        print(f"  uri: {doc.content.uri if doc.content.uri else 'None'}")
    
    print(f"\n=== Struct Data ===")
    if doc.struct_data:
        print(f"Struct data keys: {list(doc.struct_data.keys())}")
        for key, value in doc.struct_data.items():
            print(f"  {key}: {value}")
    
    print(f"\n=== JSON Data ===")
    print(f"Has json_data: {bool(doc.json_data)}")
    if doc.json_data:
        print(f"JSON data: {doc.json_data}")
    
    break

