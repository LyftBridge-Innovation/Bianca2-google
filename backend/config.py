"""Environment variables and constants."""
import os
from dotenv import load_dotenv

load_dotenv()

# Gemini API key (shared with voice pipeline)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Google Workspace CLI (gws) configuration
# The gws CLI is used for all Gmail/Calendar API calls.
# Per-user OAuth tokens are minted from refresh tokens stored in Firestore.
GWS_CLI_PATH = os.getenv("GWS_CLI_PATH", "gws")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
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
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")  # Regional endpoint for Gemini

# Rate Limiting Strategy (handles 429 errors):
# - Using gemini-2.5-flash (stable, available until June 2026)
# - max_retries=6 with exponential backoff (4s, 8s, 16s, 32s, 64s, 128s)
# - For higher limits: Request quota increase or use Provisioned Throughput

# Memory retrieval configuration (Phase 3C)
MEMORY_RECENCY_DAYS_DEFAULT = int(os.getenv("MEMORY_RECENCY_DAYS_DEFAULT", "30"))
MEMORY_RECENCY_DAYS_FALLBACK = int(os.getenv("MEMORY_RECENCY_DAYS_FALLBACK", "90"))
MEMORY_MAX_RESULTS = int(os.getenv("MEMORY_MAX_RESULTS", "5"))
MEMORY_MIN_RESULTS_THRESHOLD = int(os.getenv("MEMORY_MIN_RESULTS_THRESHOLD", "3"))

# Assistant configuration
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Bianc.ai")
