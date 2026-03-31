"""Configuration settings for the voice pipeline."""
import os
from dotenv import load_dotenv

# Load .env from project root (searches up the directory tree)
load_dotenv()

# ── API ───────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# AI Studio model (used when GOOGLE_API_KEY is set — local dev)
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

# Vertex AI Live model (reserved for future use)
VERTEX_MODEL = "gemini-2.0-flash-live-001"

# ── Audio ─────────────────────────────────────────────────────────────────────
# pyaudio is only needed for local mic/speaker (not in FastAPI server context)
try:
    import pyaudio as _pyaudio
    FORMAT = _pyaudio.paInt16
except ImportError:
    FORMAT = None  # Not available in server/test environments

CHANNELS = 1
SEND_SAMPLE_RATE    = 16000  # Microphone input
RECEIVE_SAMPLE_RATE = 24000  # Speaker output
CHUNK_SIZE = 1024

# ── Queue ─────────────────────────────────────────────────────────────────────
MIC_QUEUE_MAX_SIZE = 50

# ── User ──────────────────────────────────────────────────────────────────────
DEFAULT_USER_ID = os.getenv("TEST_USER_ID", "dev_user_1")

# ── Debug ─────────────────────────────────────────────────────────────────────
DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "false").lower() == "true"
