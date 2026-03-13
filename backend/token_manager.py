"""Per-user Google access token management with in-memory cache."""
import os
import time
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from models import FirestoreCollections

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
TOKEN_URI = "https://oauth2.googleapis.com/token"

# In-memory cache: {user_id: (access_token, expiry_timestamp)}
_token_cache: dict[str, tuple[str, float]] = {}
_BUFFER_SECONDS = 300  # Refresh 5 min before expiry

_fs = None


def _get_fs():
    global _fs
    if _fs is None:
        _fs = FirestoreCollections()
    return _fs


def get_access_token(user_id: str) -> str:
    """
    Return a valid Google access token for the given user.
    Reads per-user refresh_token from Firestore, caches access tokens in memory.
    Raises ValueError if user has no refresh_token.
    """
    # Check cache
    if user_id in _token_cache:
        token, expiry = _token_cache[user_id]
        if time.time() < expiry - _BUFFER_SECONDS:
            return token

    # Get refresh_token from Firestore
    fs = _get_fs()
    user = fs.get_user(user_id)
    if not user or not user.google_refresh_token:
        raise ValueError(
            f"No refresh token stored for user {user_id}. User must re-authenticate."
        )

    # Build Credentials and refresh
    creds = Credentials(
        token=None,
        refresh_token=user.google_refresh_token,
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri=TOKEN_URI,
    )
    creds.refresh(Request())

    if not creds.token:
        raise ValueError(f"Failed to refresh access token for user {user_id}")

    # Cache
    expiry = creds.expiry.timestamp() if creds.expiry else time.time() + 3600
    _token_cache[user_id] = (creds.token, expiry)
    logger.debug("Refreshed token for user %s", user_id)

    return creds.token
