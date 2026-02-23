"""Environment variables and constants."""
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
TEST_USER_ID = os.getenv("TEST_USER_ID", "dev_user_1")

# Firebase/Firestore configuration
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
FIREBASE_DATABASE_NAME = os.getenv("FIREBASE_DATABASE_NAME", "(default)")

# Vertex AI Search configuration (Phase 3B/3C)
VERTEX_DATASTORE_ID = os.getenv("VERTEX_DATASTORE_ID")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "global")
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", FIREBASE_PROJECT_ID)

# Vertex AI Gemini configuration (uses Google Cloud credits)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", FIREBASE_PROJECT_ID)
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")  # Gemini models available here

# Memory retrieval configuration (Phase 3C)
MEMORY_RECENCY_DAYS_DEFAULT = int(os.getenv("MEMORY_RECENCY_DAYS_DEFAULT", "30"))
MEMORY_RECENCY_DAYS_FALLBACK = int(os.getenv("MEMORY_RECENCY_DAYS_FALLBACK", "90"))
MEMORY_MAX_RESULTS = int(os.getenv("MEMORY_MAX_RESULTS", "5"))
MEMORY_MIN_RESULTS_THRESHOLD = int(os.getenv("MEMORY_MIN_RESULTS_THRESHOLD", "3"))

# Assistant configuration
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Bianca")
