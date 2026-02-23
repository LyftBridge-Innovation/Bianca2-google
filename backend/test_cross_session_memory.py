"""Test cross-session memory retrieval - Phase 3C validation."""
import requests
import json
import time

BASE_URL = "http://localhost:8000"
USER_ID = "test_memory_user"

print("=" * 70)
print("CROSS-SESSION MEMORY TEST")
print("=" * 70)

# Session A - Create conversation with specific details
print("\n=== SESSION A: Creating conversation with details ===")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "user_id": USER_ID,
        "message": "I have an important meeting with Sarah Johnson tomorrow at 2pm to discuss the Q1 budget proposal."
    },
    timeout=30
)
session_a_data = response.json()
session_a_id = session_a_data["session_id"]
print(f"Session A ID: {session_a_id}")
print(f"Response: {session_a_data['response'][:150]}...")

# Wait a moment
time.sleep(2)

# Session B - Start NEW session (should trigger summarization of Session A)
print("\n=== SESSION B: Starting NEW session ===")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "user_id": USER_ID,
        "message": "Hello, how are you?"
    },
    timeout=30
)
session_b_data = response.json()
session_b_id = session_b_data["session_id"]
print(f"Session B ID: {session_b_id}")
print(f"Different session confirmed: {session_a_id != session_b_id}")

# Wait for background summarization to complete
print("\n⏳ Waiting 10 seconds for background summarization...")
time.sleep(10)

# Check if Session A was summarized
print("\n=== Checking Session A Status ===")
response = requests.get(f"{BASE_URL}/chat/session/{session_a_id}")
session_a = response.json()
print(f"Session A status: {session_a.get('status', 'unknown')}")
if session_a.get('status') == 'summarized':
    print(f"✅ Event memory ID: {session_a.get('summary_event_id')}")
    print(f"✅ Entity memory ID: {session_a.get('summary_entity_id')}")
else:
    print(f"⚠️  Status: {session_a.get('status')}")

# Test memory retrieval endpoint
print("\n=== Testing Memory Retrieval ===")
response = requests.post(
    f"{BASE_URL}/admin/test-memory-retrieval",
    json={
        "query": "meeting Sarah Johnson budget",
        "user_id": USER_ID
    }
)
memory_test = response.json()
print(f"Memories found: {memory_test.get('total_count', 0)}")
if memory_test.get('total_count', 0) > 0:
    print("Event memories:")
    for mem in memory_test.get('event_memories', []):
        print(f"  - {mem[:100]}")
    print("Entity memories:")
    for mem in memory_test.get('entity_memories', []):
        print(f"  - {mem[:100]}")

# Session B continued - Ask about previous conversation
print("\n=== SESSION B: Asking about previous conversation ===")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "user_id": USER_ID,
        "session_id": session_b_id,
        "message": "What meeting did I tell you about? Who is it with and what time?"
    },
    timeout=30
)
test_data = response.json()
print(f"\nBianca's Response:\n{test_data['response']}")

# Verify memory usage
response_text = test_data['response'].lower()
mentions_sarah = 'sarah' in response_text
mentions_time = '2pm' in response_text or '2 pm' in response_text or 'two pm' in response_text or '2:00' in response_text
mentions_budget = 'budget' in response_text or 'q1' in response_text

print("\n" + "=" * 70)
print("VERIFICATION RESULTS")
print("=" * 70)
print(f"✓ Mentions Sarah Johnson: {mentions_sarah}")
print(f"✓ Mentions 2pm: {mentions_time}")
print(f"✓ Mentions budget/Q1: {mentions_budget}")

if mentions_sarah or mentions_time or mentions_budget:
    print("\n✅ CROSS-SESSION MEMORY WORKING!")
    print("Bianca successfully retrieved and used memories from previous session.")
else:
    print("\n❌ MEMORY NOT RETRIEVED")
    print("Bianca did not recall details from the previous conversation.")
    
print("=" * 70)
