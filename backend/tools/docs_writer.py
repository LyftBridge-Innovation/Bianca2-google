"""Google Docs writer — create and populate documents via Google Docs API."""
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from token_manager import get_access_token

logger = logging.getLogger(__name__)


def create_google_doc(user_id: str, title: str, content: str) -> dict:
    """Create a new Google Doc with the given title and body text."""
    token = get_access_token(user_id)
    creds = Credentials(token=token)
    service = build("docs", "v1", credentials=creds)

    # Create the document
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # Insert content
    if content.strip():
        service.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content,
                        }
                    }
                ]
            },
        ).execute()

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    logger.info("Created Google Doc '%s' for user %s: %s", title, user_id, url)

    return {"title": title, "doc_id": doc_id, "url": url}
