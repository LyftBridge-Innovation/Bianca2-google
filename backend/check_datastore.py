"""Quick script to check Vertex AI Search datastore configuration."""
import os
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1 as discoveryengine

# Load environment
load_dotenv()

project_id = os.getenv("FIREBASE_PROJECT_ID")
datastore_id = os.getenv("VERTEX_DATASTORE_ID")
location = os.getenv("VERTEX_LOCATION", "global")

print(f"Project: {project_id}")
print(f"Datastore: {datastore_id}")
print(f"Location: {location}\n")

# Get datastore info
client = discoveryengine.DataStoreServiceClient()
datastore_path = client.data_store_path(
    project=project_id,
    location=location,
    data_store=datastore_id
)

datastore = client.get_data_store(name=datastore_path)

print("=== Datastore Info ===")
print(f"Name: {datastore.name}")
print(f"Display Name: {datastore.display_name}")
print(f"Industry Vertical: {datastore.industry_vertical}")
print(f"Content Config: {datastore.content_config}")
print(f"Solution Types: {datastore.solution_types}")
print(f"Create Time: {datastore.create_time}")
