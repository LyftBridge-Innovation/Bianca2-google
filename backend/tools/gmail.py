"""Gmail tools — read, send, and draft emails on behalf of a user."""
import base64
from email.mime.text import MIMEText
from fastapi import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tools.google_auth import GoogleAuthManager

auth_manager = GoogleAuthManager()


def _service(user_id: str):
    creds = auth_manager.get_credentials(user_id)
    return build("gmail", "v1", credentials=creds)


def list_emails(user_id: str, max_results: int = 10) -> list[dict]:
    """Returns recent emails: id, subject, sender, date, snippet."""
    try:
        service = _service(user_id)
        result = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = result.get("messages", [])

        emails = []
        for msg in messages:
            m = service.users().messages().get(userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
            emails.append({
                "id": m["id"],
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": m.get("snippet", ""),
            })
        return emails
    except HttpError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


def get_email(user_id: str, email_id: str) -> dict:
    """Returns full email body and metadata for a given email ID."""
    try:
        service = _service(user_id)
        m = service.users().messages().get(userId="me", id=email_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}

        body = ""
        payload = m["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
        elif "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        return {
            "id": m["id"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body,
        }
    except HttpError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Email {email_id} not found.")
        raise HTTPException(status_code=e.status_code, detail=str(e))


def send_email(user_id: str, to: str, subject: str, body: str) -> dict:
    """Sends an email on behalf of the user. Only call when user explicitly confirms."""
    try:
        service = _service(user_id)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"id": sent["id"], "status": "sent"}
    except HttpError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


def draft_email(user_id: str, to: str, subject: str, body: str) -> dict:
    """Saves an email as a draft. Default action — does NOT send."""
    try:
        service = _service(user_id)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return {"id": draft["id"], "status": "drafted"}
    except HttpError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
