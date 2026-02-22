"""Debug script to check Vertex AI Search document structure."""
from google.cloud import discoveryengine_v1beta as discoveryengine
import os

# Setup
VERTEX_DATASTORE_ID = os.getenv("VERTEX_DATASTORE_ID")
VERTEX_LOCATION = "global"
VERTEX_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

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
    print(f"HasField content: {doc.HasField('content')}")
    print(f"Content: {doc.content}")
    print(f"JSON data: {doc.jsonData if doc.HasField('json_data') else 'N/A'}")
    print(f"Struct data keys: {list(doc.struct_data.keys())}")
    print(f"Struct data: {dict(doc.struct_data)}")
    break
