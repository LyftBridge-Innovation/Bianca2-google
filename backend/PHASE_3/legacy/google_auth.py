"""Google OAuth token manager. MVP: hardcoded refresh token from env. Later: swap to Firestore lookup per user."""
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar",
]


class GoogleAuthManager:
    def get_credentials(self, user_id: str) -> Credentials:
        """
        Returns valid Google credentials for a user.
        MVP: ignores user_id and uses env refresh token.
        Later: look up user_id in Firestore for their stored token.
        """
        creds = Credentials(
            token=None,
            refresh_token=GOOGLE_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )
        return self.refresh_if_expired(creds)

    def refresh_if_expired(self, creds: Credentials) -> Credentials:
        """Silently refreshes the access token if it is expired or within 5 minutes of expiry."""
        expiry = creds.expiry
        near_expiry = expiry and expiry < datetime.now(timezone.utc) + timedelta(minutes=5)
        if not creds.valid or near_expiry:
            creds.refresh(Request())
        return creds
