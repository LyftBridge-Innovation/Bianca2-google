"""Google OAuth callback endpoint — exchanges auth code for tokens."""
import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from models import FirestoreCollections, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

fs = FirestoreCollections()

# Web Application client credentials (for browser auth-code popup flow).
# These MUST be a "Web Application" type OAuth client — NOT Desktop.
# The Desktop client (GOOGLE_CLIENT_ID) is used for refreshing stored tokens.
WEB_CLIENT_ID = os.getenv("GOOGLE_WEB_CLIENT_ID")
WEB_CLIENT_SECRET = os.getenv("GOOGLE_WEB_CLIENT_SECRET")

BASE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _build_all_scopes() -> list[str]:
    """Build deduplicated scope list from base scopes + all YAML skill scopes."""
    all_scopes = set(BASE_SCOPES)
    try:
        from skills_loader import get_all_scopes
        all_scopes.update(get_all_scopes())
    except Exception as e:
        logger.warning("Could not load YAML skill scopes: %s", e)
    return sorted(all_scopes)


class GoogleCallbackRequest(BaseModel):
    code: str


class GoogleCallbackResponse(BaseModel):
    user_id: str
    name: str
    email: str
    picture: str


@router.post("/google/callback", response_model=GoogleCallbackResponse)
async def google_callback(request: GoogleCallbackRequest):
    """
    Exchange a Google authorization code for tokens.
    Stores refresh_token per user in Firestore and returns verified user info.
    """
    try:
        if not WEB_CLIENT_ID or not WEB_CLIENT_SECRET:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_WEB_CLIENT_ID and GOOGLE_WEB_CLIENT_SECRET must be set in backend .env",
            )

        # Build OAuth flow to exchange the auth code
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": WEB_CLIENT_ID,
                    "client_secret": WEB_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=_build_all_scopes(),
            redirect_uri="postmessage",  # Required for JS popup auth-code flow
        )

        flow.fetch_token(code=request.code)
        credentials = flow.credentials

        # Verify the ID token server-side
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            WEB_CLIENT_ID,
        )

        user_id = id_info["sub"]
        email = id_info.get("email", "")
        name = id_info.get("name", "")
        picture = id_info.get("picture", "")

        # Store / update user with refresh token in Firestore
        existing_user = fs.get_user(user_id)
        refresh_token = credentials.refresh_token

        if existing_user:
            # Only overwrite refresh_token if Google returned a new one
            # (Google only returns refresh_token on the first consent)
            if refresh_token:
                existing_user.google_refresh_token = refresh_token
            existing_user.email = email
            existing_user.full_name = name
            fs.create_or_update_user(existing_user)
        else:
            if not refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail="No refresh token received. Please revoke app access in Google Account settings and try again.",
                )
            user = User(
                user_id=user_id,
                email=email,
                full_name=name,
                google_refresh_token=refresh_token,
            )
            fs.create_or_update_user(user)

        logger.info("User authenticated: %s (%s)", email, user_id)

        return GoogleCallbackResponse(
            user_id=user_id,
            name=name,
            email=email,
            picture=picture,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("OAuth callback error: %s", e)
        raise HTTPException(status_code=500, detail=f"Authentication failed: {e}")


@router.get("/scopes")
def get_required_scopes():
    """Returns the OAuth scopes needed for the current skill configuration."""
    return {"scopes": _build_all_scopes()}
