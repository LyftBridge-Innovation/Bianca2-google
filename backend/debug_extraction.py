"""Debug summarization extraction to see what LLM is returning."""
import os
from dotenv import load_dotenv
load_dotenv()

from models import FirestoreCollections
from summarization import extract_event_memory, extract_entity_memory

# Get the test session
fs = FirestoreCollections()
session = fs.get_session("1e6d9149-609d-4b99-8160-91407a225177")

print("=== SESSION DETAILS ===")
print(f"Messages: {len(session.messages)}")
for msg in session.messages:
    print(f"  {msg.role}: {msg.content[:100]}")
print(f"Tool calls: {len(session.tool_calls)}")

print("\n=== EXTRACTING EVENT MEMORY ===")
try:
    event_memory = extract_event_memory(session)
    print(f"Result length: {len(event_memory)}")
    print(f"Content:\n{event_memory}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n=== EXTRACTING ENTITY MEMORY ===")
try:
    entity_memory = extract_entity_memory(session)
    print(f"Result length: {len(entity_memory)}")
    print(f"Content:\n{entity_memory}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
